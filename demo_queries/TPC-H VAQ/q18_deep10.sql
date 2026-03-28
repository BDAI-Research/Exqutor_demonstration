SELECT /*+ IndexScan(partsupp_deep_10 deep_hnsw_10) */
    c_name, c_custkey, o_orderkey, o_orderdate, o_totalprice, l_quantity
FROM customer_10, orders_10, lineitem_10, partsupp_deep_10
WHERE o_orderkey IN (
    SELECT l_orderkey
    FROM lineitem_10
    GROUP BY l_orderkey
    HAVING SUM(l_quantity) > 200
  )
  AND c_custkey = o_custkey
  AND o_orderkey = l_orderkey
  AND ps_partkey = l_partkey
  AND ps_suppkey = l_suppkey
  AND ps_embedding <-> :'VEC'::vector(96) < 0.86
ORDER BY ps_embedding <-> :'VEC'::vector(96);
