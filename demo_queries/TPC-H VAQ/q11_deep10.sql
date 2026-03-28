SELECT /*+ IndexScan(partsupp_deep_10 deep_hnsw_10) */
    ps_partkey
FROM
    partsupp_deep_10,
    supplier_10,
    nation_10
WHERE
    ps_suppkey = s_suppkey
    AND s_nationkey = n_nationkey
    AND n_name = 'ARGENTINA'
    AND ps_embedding <-> :'VEC'::vector(96) < 0.86
ORDER BY
    ps_embedding <-> :'VEC'::vector(96);