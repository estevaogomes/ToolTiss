select  nr_sequencia as nr_seq_glosa_evento_p, 
        'BDTOOLS' as nm_usuario_p from PLS_GLOSA_EVENTO
where ie_evento = 'IA';

--procedure pls_utiliza_glosa_evento(	nr_seq_glosa_evento_p	number,	nm_usuario_p		Varchar2) 

select * from pls_ocorrencia
where NR_SEQ_CLASSIF  in (2,3,4);

update pls_ocorrencia
set IE_SITUACAO = 'I'
where NR_SEQ_CLASSIF  in (2,3,4);


select * from pls_analise_conta_temp
where nm_usuario_nrec = 'WebService'
;

--pls_gerar_lib_analise (nr_seq_analise_p		number,	cd_stabelecimento_pe	number,	nm_usuario_p)