SELECT /*+ IndexScan(partsupp_deep_10 deep_hnsw_10) */
    l_orderkey, o_orderdate, o_shippriority
FROM
    customer_10, orders_10, lineitem_10, partsupp_deep_10
WHERE
    c_mktsegment = 'HOUSEHOLD'
    AND c_custkey = o_custkey
    AND l_orderkey = o_orderkey
    AND o_orderdate < DATE '1995-03-14'
    AND l_shipdate > DATE '1995-03-14'
    AND ps_partkey = l_partkey
    AND ps_suppkey = l_suppkey
    AND ps_embedding <-> :'VEC'::vector(96) < 0.925
ORDER BY
    ps_embedding <-> :'VEC'::vector(96);
