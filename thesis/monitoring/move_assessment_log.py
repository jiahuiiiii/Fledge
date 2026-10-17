"""Append-only saved-price observations, including assessments without events.

No source/model/Telegram requests. The independent report can count qualifying
episodes even if event publication or the worker later fails.
"""
from uuid import uuid4
from psycopg.types.json import Jsonb
from . import price_moves


def record(conn,owner,run_id,observations,*,at,preview):
    for value in observations:
        measured=value['measure']
        conn.execute('INSERT INTO move_assessments VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)',
            (uuid4(),owner,run_id,value['instrument_id'],at,value['quote_id'],value['status'],
             bool(measured and measured['triggered']),value['already_claimed'],preview,price_moves.POLICY,
             Jsonb(dict(thresholds=value['thresholds'],measure=measured))))
    return len(observations)
