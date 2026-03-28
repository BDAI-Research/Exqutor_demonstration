select /*+ IndexScan(partsupp_deep_10 deep_hnsw_10) */
	l_shipmode
from
    orders_10,
    lineitem_10,
    partsupp_deep_10
where
    o_orderkey = l_orderkey
    and l_shipmode in ('RAIL', 'SHIP')
    and l_commitdate < l_receiptdate
    and l_shipdate < l_commitdate
    and l_receiptdate >= date '1994-01-01'
    and l_receiptdate < date '1994-01-01' + interval '1' year
    and ps_partkey = l_partkey
    and ps_suppkey = l_suppkey
    AND ps_embedding <-> :'VEC'::vector(96) < 0.86
ORDER BY
    ps_embedding <-> :'VEC'::vector(96);