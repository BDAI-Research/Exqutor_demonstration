SELECT /*+ IndexScan(partsupp_deep_10 deep_hnsw_10) */
    n_name
FROM
    customer_10,
    orders_10,
    lineitem_10,
    supplier_10,
    nation_10,
    region_10,
    partsupp_deep_10
WHERE
    c_custkey = o_custkey
    AND l_orderkey = o_orderkey
    AND l_suppkey = s_suppkey
    AND c_nationkey = s_nationkey
    AND s_nationkey = n_nationkey
    AND n_regionkey = r_regionkey
    AND r_name = 'MIDDLE EAST'
    AND o_orderdate >= DATE '1993-01-01'
    AND o_orderdate < DATE '1993-01-01' + INTERVAL '1' YEAR
    AND ps_partkey = l_partkey
    AND ps_suppkey = l_suppkey
    AND ps_embedding <-> :'VEC'::vector(96) < 0.86
ORDER BY
    ps_embedding <-> :'VEC'::vector(96);