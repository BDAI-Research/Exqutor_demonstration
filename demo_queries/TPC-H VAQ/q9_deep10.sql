SELECT /*+ IndexScan(partsupp_deep_10 deep_hnsw_10) */
    nation,
    o_year,
    SUM(amount) AS sum_profit
FROM
    (
        SELECT
            n_name AS nation,
            extract(YEAR FROM o_orderdate) AS o_year,
            l_extendedprice * (1 - l_discount) - ps_supplycost * l_quantity AS amount
        FROM
            part_10,
            supplier_10,
            lineitem_10,
            partsupp_deep_10,
            orders_10,
            nation_10
        WHERE
            s_suppkey = l_suppkey
            AND ps_suppkey = l_suppkey
            AND ps_partkey = l_partkey
            AND p_partkey = l_partkey
            AND o_orderkey = l_orderkey
            AND s_nationkey = n_nationkey
            AND p_name LIKE '%almond%'
            and ps_embedding <-> :'VEC'::vector(96) < 0.86
        ORDER BY
            ps_embedding <-> :'VEC'::vector(96)
    ) as profit
group by
    nation,
    o_year
order by
    nation,
    o_year desc
LIMIT 1;