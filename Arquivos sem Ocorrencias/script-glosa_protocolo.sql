--- GLOSA PROTOCOLO

SELECT
    nr_seq_motivo_glosa,
    cd_motivo_glosa,
    ds_motivo_glosa,
    tot_glosa,
    ds_tipo,
    ie_tipo,
    ds_grupo_glosa
FROM (
    SELECT
        q.*,
        ROW_NUMBER() OVER (
            PARTITION BY nr_seq_motivo_glosa
            ORDER BY ie_tipo, nr_seq_motivo_glosa
        ) AS rn
    FROM (
        SELECT
            nr_seq_motivo_glosa,
            cd_motivo_glosa,
            ds_motivo_glosa,
            tot_glosa,
            ds_tipo,
            ie_tipo,
            ds_grupo_glosa
        FROM (
            SELECT
                a.nr_seq_ocorrencia AS nr_seq_motivo_glosa,
                SUBSTR(
                    pls_obter_dados_ocorrencia(
                        a.nr_seq_ocorrencia, 'C'
                    ), 1, 255
                ) AS cd_motivo_glosa,
                SUBSTR(
                    pls_obter_dados_ocorrencia(
                        a.nr_seq_ocorrencia, 'D'
                    ), 1, 255
                ) AS ds_motivo_glosa,
                pls_obter_tot_conta_oco(
                    nr_seq_protocolo,
                    nr_seq_ocorrencia
                ) AS tot_glosa,
                'Ocorrência' AS ds_tipo,
                'O' AS ie_tipo,
                NULL AS ds_grupo_glosa
            FROM
                pls_ocorrencia_benef a,
                pls_conta b,
                pls_protocolo_conta c
            WHERE
                a.nr_seq_conta = b.nr_sequencia
                AND b.nr_seq_protocolo = c.nr_sequencia
                AND c.nm_usuario = 'WebService'

            UNION

            SELECT
                nr_seq_motivo_glosa,
                SUBSTR(
                    tiss_obter_motivo_glosa(
                        nr_seq_motivo_glosa, 'C'
                    ), 1, 255
                ) AS cd_motivo_glosa,
                SUBSTR(
                    tiss_obter_motivo_glosa(
                        nr_seq_motivo_glosa, 'D'
                    ), 1, 255
                ) AS ds_motivo_glosa,
                pls_obter_tot_conta_glosa(
                    nr_seq_protocolo,
                    nr_seq_motivo_glosa
                ) AS tot_glosa,
                'Glosa' AS ds_tipo,
                'G' AS ie_tipo,
                ds_grupo_glosa
            FROM (
                SELECT DISTINCT
                    a.nr_seq_motivo_glosa,
                    b.nr_seq_protocolo,
                    a.ds_observacao,
                    SUBSTR(
                        obter_valor_dominio(
                            1771, d.ie_grupo_glosa
                        ), 1, 50
                    ) AS ds_grupo_glosa
                FROM
                    pls_conta_glosa a,
                    pls_conta b,
                    pls_conta_proc c,
                    tiss_motivo_glosa d,
                    pls_protocolo_conta e
                WHERE
                    a.nr_seq_conta_proc = c.nr_sequencia
                    AND b.nr_sequencia = c.nr_seq_conta
                    AND a.nr_seq_motivo_glosa = d.nr_sequencia
                    AND b.nr_seq_protocolo = e.nr_sequencia
                    AND e.nm_usuario = 'WebService'
                    AND NOT EXISTS (
                        SELECT x.nr_sequencia
                        FROM pls_ocorrencia_benef x
                        WHERE x.nr_seq_glosa = a.nr_sequencia
                    )

                UNION

                SELECT DISTINCT
                    a.nr_seq_motivo_glosa,
                    b.nr_seq_protocolo,
                    a.ds_observacao,
                    SUBSTR(
                        obter_valor_dominio(
                            1771, d.ie_grupo_glosa
                        ), 1, 50
                    ) AS ds_grupo_glosa
                FROM
                    pls_conta_glosa a,
                    pls_conta b,
                    pls_conta_mat c,
                    tiss_motivo_glosa d,
                    pls_protocolo_conta e
                WHERE
                    a.nr_seq_conta_mat = c.nr_sequencia
                    AND b.nr_sequencia = c.nr_seq_conta
                    AND b.nr_seq_protocolo = e.nr_sequencia
                    AND a.nr_seq_motivo_glosa = d.nr_sequencia
                    AND e.nm_usuario = 'WebService'
                    AND NOT EXISTS (
                        SELECT x.nr_sequencia
                        FROM pls_ocorrencia_benef x
                        WHERE x.nr_seq_glosa = a.nr_sequencia
                    )

                UNION

                SELECT DISTINCT
                    a.nr_seq_motivo_glosa,
                    b.nr_seq_protocolo,
                    a.ds_observacao,
                    SUBSTR(
                        obter_valor_dominio(
                            1771, c.ie_grupo_glosa
                        ), 1, 50
                    ) AS ds_grupo_glosa
                FROM
                    pls_conta_glosa a,
                    pls_conta b,
                    tiss_motivo_glosa c,
                    pls_protocolo_conta d
                WHERE
                    b.nr_sequencia = a.nr_seq_conta
                    AND a.nr_seq_motivo_glosa = c.nr_sequencia
                    AND b.nr_seq_protocolo = d.nr_sequencia
                    AND d.nm_usuario = 'WebService'
                    AND a.nr_seq_conta_mat IS NULL
                    AND a.nr_seq_conta_proc IS NULL
                    AND NOT EXISTS (
                        SELECT x.nr_sequencia
                        FROM pls_ocorrencia_benef x
                        WHERE x.nr_seq_glosa = a.nr_sequencia
                    )
            )
        )
    ) q
)
WHERE rn = 1;