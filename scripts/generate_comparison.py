#!/usr/bin/env python3
"""
Generate proxy database comparison CSV.

Compares the reference presto2k proxy database against a custom run's proxy
selection (from query_params.json + cleaning_report.json), using TSID as the
matching key. Metadata is enriched from the lipdverseQuery CSV.

Usage:
    python generate_comparison.py <presto2k_pdb.pkl> <query_params.json> \
        <cleaning_report.json> <output.csv>
"""
import csv
import json
import os
import pickle
import sys
import tempfile
import zipfile
import urllib.request

import numpy as np

LIPDVERSE_QUERY_URL = 'https://lipdverse.org/lipdverse/lipdverseQuery.zip'


class GenericUnpickler(pickle.Unpickler):
    """Unpickle cfr objects without needing the cfr package installed."""
    def find_class(self, module, name):
        try:
            return super().find_class(module, name)
        except (ModuleNotFoundError, AttributeError):
            class Generic:
                def __init__(self, *args, **kwargs):
                    pass
                def __setstate__(self, state):
                    self.__dict__.update(state if isinstance(state, dict) else {})
            Generic.__name__ = name
            Generic.__module__ = module
            return Generic


def na(val):
    """Return '' for NA/empty values."""
    if val is None or val == 'NA' or val == '':
        return ''
    return val


def download_lipdverse_csv(cache_dir=None):
    """Download and extract lipdverseQuery.csv, returning the path."""
    if cache_dir is None:
        cache_dir = tempfile.gettempdir()
    csv_path = os.path.join(cache_dir, 'lipdverseQuery.csv')
    if os.path.exists(csv_path):
        return csv_path
    zip_path = os.path.join(cache_dir, 'lipdverseQuery.zip')
    print(f'Downloading {LIPDVERSE_QUERY_URL} ...')
    urllib.request.urlretrieve(LIPDVERSE_QUERY_URL, zip_path)
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            if member.endswith('.csv'):
                zf.extract(member, cache_dir)
                extracted = os.path.join(cache_dir, member)
                if extracted != csv_path:
                    os.rename(extracted, csv_path)
                break
    print('  Extracted.')
    return csv_path


def load_lipdverse_lookup(csv_path):
    """Build TSID lookup dicts from the lipdverseQuery CSV."""
    tsid_to_dsname = {}
    tsid_to_comp = {}
    tsid_to_meta = {}
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tsid = row['paleoData_TSid']
            dsname = row['dataSetName']
            comp = row['paleoData_mostRecentCompilations']
            if not tsid:
                continue
            tsid_to_dsname[tsid] = dsname
            if comp and comp != 'NA':
                tsid_to_comp[tsid] = comp
            elif tsid not in tsid_to_comp:
                tsid_to_comp[tsid] = ''
            if tsid not in tsid_to_meta:
                tsid_to_meta[tsid] = dict(row)
            else:
                existing = tsid_to_meta[tsid]
                for k in ['geo_latitude', 'geo_longitude', 'geo_elevation',
                          'archiveType', 'paleoData_proxy',
                          'interpretation1_seasonality', 'minAge', 'maxAge']:
                    if (not existing.get(k) or existing.get(k) == 'NA') \
                            and row.get(k) and row.get(k) != 'NA':
                        existing[k] = row[k]
    return tsid_to_dsname, tsid_to_comp, tsid_to_meta


def get_csv_meta(tsid, tsid_to_meta):
    """Pull metadata fields from the lipdverseQuery CSV for a given TSID."""
    meta = tsid_to_meta.get(tsid)
    if not meta:
        return {'ptype': '', 'lat': '', 'lon': '', 'elev': '',
                'seasonality': '', 'time_start': '', 'time_end': '', 'n_obs': ''}
    return {
        'ptype': na(meta.get('archiveType', '')),
        'lat': na(meta.get('geo_latitude', '')),
        'lon': na(meta.get('geo_longitude', '')),
        'elev': na(meta.get('geo_elevation', '')),
        'seasonality': na(meta.get('interpretation1_seasonality', '')),
        'time_start': na(meta.get('minAge', '')),
        'time_end': na(meta.get('maxAge', '')),
        'n_obs': '',
    }


def get_record_info(pobj):
    """Extract metadata from a cfr ProxyRecord object."""
    t = getattr(pobj, 'time', None)
    if t is not None and len(t) > 0:
        t_arr = np.asarray(t, dtype=float)
        return {
            'ptype': getattr(pobj, 'ptype', ''),
            'lat': round(float(getattr(pobj, 'lat', 0)), 4)
                   if getattr(pobj, 'lat', None) is not None else '',
            'lon': round(float(getattr(pobj, 'lon', 0)), 4)
                   if getattr(pobj, 'lon', None) is not None else '',
            'elev': getattr(pobj, 'elev', ''),
            'seasonality': str(getattr(pobj, 'seasonality', '')),
            'time_start': int(np.floor(t_arr.min())),
            'time_end': int(np.floor(t_arr.max())),
            'n_obs': len(t_arr),
        }
    return {'ptype': getattr(pobj, 'ptype', ''), 'lat': '', 'lon': '',
            'elev': '', 'seasonality': '', 'time_start': '', 'time_end': '',
            'n_obs': ''}


def main(presto2k_path, query_params_path, cleaning_report_path, output_path):
    # ── Load lipdverseQuery CSV ──
    csv_path = download_lipdverse_csv()
    print('Loading lipdverseQuery.csv ...')
    tsid_to_dsname, tsid_to_comp, tsid_to_meta = load_lipdverse_lookup(csv_path)
    n_with_comp = sum(1 for v in tsid_to_comp.values() if v)
    print(f'  {len(tsid_to_dsname)} TSIDs loaded, {n_with_comp} with compilation')

    # ── Load presto2k ProxyDatabase ──
    with open(presto2k_path, 'rb') as f:
        presto2k_pdb = GenericUnpickler(f).load()
    print(f'\npresto2k: {len(presto2k_pdb.records)} records')

    # ── Load cleaning report (optional) and query params ──
    cleaning = []
    if cleaning_report_path and os.path.exists(cleaning_report_path):
        with open(cleaning_report_path, encoding='utf-8') as f:
            cleaning = json.load(f)
        print(f'Loaded cleaning report: {len(cleaning)} groups')
    else:
        print('No cleaning report — using all query TSIDs')

    with open(query_params_path, encoding='utf-8') as f:
        qp = json.load(f)

    all_query_tsids = set(qp.get('tsids', []))
    cleaning_removed = set()
    for group in cleaning:
        for rec in group['records']:
            if rec['decision'] == 'remove':
                cleaning_removed.add(rec['tsid'])

    custom_tsids = all_query_tsids - cleaning_removed
    print(f'custom_run: {len(custom_tsids)} effective TSIDs '
          f'(from {len(all_query_tsids)} query - {len(cleaning_removed)} removed)')

    # ── Extract TSID from presto2k PIDs ──
    all_known_tsids = (set(tsid_to_dsname.keys())
                       | all_query_tsids
                       | {rec['tsid'] for g in cleaning for rec in g['records']})
    presto2k_tsid = {}

    for pid in presto2k_pdb.records:
        matched = False
        for tsid in all_known_tsids:
            if pid.endswith('_' + tsid):
                presto2k_tsid[pid] = tsid
                matched = True
                break
        if not matched:
            for tsid, dsname in tsid_to_dsname.items():
                if pid.startswith(dsname + '_'):
                    presto2k_tsid[pid] = pid[len(dsname) + 1:]
                    matched = True
                    break
        if not matched:
            presto2k_tsid[pid] = None

    n_matched = sum(1 for v in presto2k_tsid.values() if v is not None)
    print(f'presto2k TSIDs extracted: {n_matched}/{len(presto2k_pdb.records)}')

    unmatched = [pid for pid, tsid in presto2k_tsid.items() if tsid is None]
    if unmatched:
        print(f'  Unmatched PIDs ({len(unmatched)}):')
        for pid in sorted(unmatched)[:10]:
            print(f'    {pid}')

    # ── TSID matching ──
    presto2k_tsid_set = {v for v in presto2k_tsid.values() if v is not None}
    both_tsids = presto2k_tsid_set & custom_tsids
    print(f'\n=== TSID matching ===')
    print(f'  presto2k TSIDs: {len(presto2k_tsid_set)}')
    print(f'  custom_run TSIDs: {len(custom_tsids)}')
    print(f'  Shared: {len(both_tsids)}')
    print(f'  presto2k only: {len(presto2k_tsid_set - custom_tsids)}')
    print(f'  custom_run only: {len(custom_tsids - presto2k_tsid_set)}')

    # ── Build rows ──
    rows = []
    seen_custom_tsids = set()

    for pid in sorted(presto2k_pdb.records.keys()):
        pobj = presto2k_pdb.records[pid]
        info = get_record_info(pobj)
        tsid = presto2k_tsid.get(pid) or ''

        # Fill missing fields from CSV
        if tsid:
            csv_meta = get_csv_meta(tsid, tsid_to_meta)
            for k in ['ptype', 'lat', 'lon', 'elev', 'seasonality',
                       'time_start', 'time_end']:
                if not info[k] and info[k] != 0:
                    info[k] = csv_meta[k]

        if tsid and tsid in custom_tsids:
            source = 'both'
            seen_custom_tsids.add(tsid)
        else:
            source = 'presto2k'

        dsname = tsid_to_dsname.get(tsid, '') if tsid else ''
        if not dsname:
            if tsid and pid.endswith('_' + tsid):
                dsname = pid[:-(len(tsid) + 1)]
            else:
                dsname = pid
        comp = tsid_to_comp.get(tsid, '') if tsid else ''

        rows.append({
            'TSID': tsid, 'record_id': pid, 'source': source,
            'dataSetName': dsname, 'ptype': info['ptype'],
            'lat': info['lat'], 'lon': info['lon'], 'elev': info['elev'],
            'seasonality': info['seasonality'],
            'time_start': info['time_start'], 'time_end': info['time_end'],
            'n_obs': info['n_obs'], 'compilation': comp,
        })

    # Custom-only TSIDs
    for tsid in sorted(custom_tsids - seen_custom_tsids):
        dsname = tsid_to_dsname.get(tsid, '')
        comp = tsid_to_comp.get(tsid, '')
        info = get_csv_meta(tsid, tsid_to_meta)

        rows.append({
            'TSID': tsid, 'record_id': dsname or tsid, 'source': 'custom_run',
            'dataSetName': dsname, 'ptype': info['ptype'],
            'lat': info['lat'], 'lon': info['lon'], 'elev': info['elev'],
            'seasonality': info['seasonality'],
            'time_start': info['time_start'], 'time_end': info['time_end'],
            'n_obs': info['n_obs'], 'compilation': comp,
        })

    # ── Write CSV ──
    fields = ['TSID', 'record_id', 'source', 'dataSetName', 'ptype', 'lat',
              'lon', 'elev', 'seasonality', 'time_start', 'time_end', 'n_obs',
              'compilation']

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    n_both = sum(1 for r in rows if r['source'] == 'both')
    n_presto2k = sum(1 for r in rows if r['source'] == 'presto2k')
    n_custom = sum(1 for r in rows if r['source'] == 'custom_run')
    n_comp = sum(1 for r in rows if r['compilation'])
    n_lat = sum(1 for r in rows if r['lat'])
    n_ptype = sum(1 for r in rows if r['ptype'])

    print(f'\n{"="*60}')
    print(f'RESULTS: {output_path}')
    print(f'  Total rows:      {len(rows)}')
    print(f'  both:            {n_both}')
    print(f'  presto2k only:   {n_presto2k}')
    print(f'  custom_run only: {n_custom}')
    print(f'  Rows with compilation:   {n_comp}/{len(rows)}')
    print(f'  Rows with lat/lon:       {n_lat}/{len(rows)}')
    print(f'  Rows with ptype:         {n_ptype}/{len(rows)}')
    print(f'{"="*60}')


if __name__ == '__main__':
    if len(sys.argv) < 4:
        print(f'Usage: {sys.argv[0]} <presto2k_pdb.pkl> <query_params.json> '
              f'<output.csv> [cleaning_report.json]')
        sys.exit(1)
    presto2k = sys.argv[1]
    query_params = sys.argv[2]
    output = sys.argv[3]
    cleaning = sys.argv[4] if len(sys.argv) > 4 else None
    main(presto2k, query_params, cleaning, output)
