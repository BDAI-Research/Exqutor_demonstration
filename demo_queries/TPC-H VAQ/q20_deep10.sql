SELECT /*+ IndexScan(partsupp_deep_10 deep_hnsw_10) */
    s_name,
    s_address,
    n_name
FROM
    supplier_10,
    nation_10
WHERE
    s_suppkey IN (
        SELECT
            ps_suppkey
        FROM
            partsupp_deep_10,
            (
                SELECT
                    l_partkey AS agg_partkey,
                    l_suppkey AS agg_suppkey,
                    0.5 * SUM(l_quantity) AS agg_quantity
                FROM
                    lineitem_10
                WHERE
                    l_shipdate >= DATE '1993-01-01'
                    AND l_shipdate < DATE '1993-01-01' + INTERVAL '1 year'
                GROUP BY
                    l_partkey,
                    l_suppkey
            ) agg_lineitem
        WHERE
            agg_partkey = ps_partkey
            AND agg_suppkey = ps_suppkey
            AND ps_partkey IN (
                SELECT
                    p_partkey
                FROM
                    part_10
                WHERE
                    p_name LIKE 'azure%'
            )
            AND ps_availqty > agg_quantity
        AND ps_embedding <-> :'VEC'::vector(96) < 0.86
    ORDER BY
        ps_embedding <-> :'VEC'::vector(96)
    )
    and s_nationkey = n_nationkey
    AND n_name = 'MOZAMBIQUE'
order by
    s_name
LIMIT 1;