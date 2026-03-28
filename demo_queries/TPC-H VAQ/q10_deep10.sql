SELECT /*+ IndexScan(partsupp_deep_10 deep_hnsw_10) */
    c_custkey,
    c_name,
    c_acctbal,
    n_name,
    c_address,
    c_phone,
    c_comment
FROM
    customer_10,
    orders_10,
    lineitem_10,
    nation_10,
    partsupp_deep_10
WHERE
    c_custkey = o_custkey
    AND l_orderkey = o_orderkey
    AND o_orderdate >= DATE '1993-11-01'
    AND o_orderdate < DATE '1993-11-01' + INTERVAL '3' MONTH
    AND l_returnflag = 'R'
    AND c_nationkey = n_nationkey
    AND ps_partkey = l_partkey
    AND ps_suppkey = l_suppkey
    AND ps_embedding <-> :'VEC'::vector(96) < 0.925
ORDER BY
    ps_embedding <-> :'VEC'::vector(96);