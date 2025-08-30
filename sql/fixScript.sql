-- Truncate table DMOVRACCF
truncate table DMOVRACCF;

-- Insert into table DMOVRACCF
insert into DMOVRACCF
With

Sales As (
    select VDCO, VDDIV, VDBR, VDINV, VDLIN, VDSTK, VDSALA, VDSALC, CBTYP, CBSMN
    from CGIIND
        left join CGIBASE on VDCO||VDDIV||VDSTK = CBCO||CBDIV||CBORD
    where VDTYP = 'L'
    ),
    
OverMapping(OA_ID, SOLD_TYPE, OA_ACC) AS (
  VALUES
    ('2N','NEW AG','321002'),
    ('5N','NEW CP','323005'),
    ('6N','NEW CWP','323006'),
    ('2U','USED AG','361012'),
    ('5U','USED CP','361025'),
    ('6U','USED CWP','361026')
    )
    
select
    a.VDCO||a.VDDIV||a.VDBR||a.VDINV||a.VDLIN||a.VDTYP||a.VDSEQ As Trade_Key,
    case
        when VHSTA = 'P' then 'Pending'
        when VHSTA = 'R' then 'Released'
        when VHSTA = 'I' then 'Invoiced' end As Status,
    a.VDBR As Branch,
    a.VDINV As Invoice,
    DATE(TIMESTAMP_FORMAT(CHAR(case when VHDTI is null or VHDTI = 0 then NULL else VHDTI end),'YYYYMMDD')) As Invoice_Date,
    a.VDLIN As Segment, 
    a.VDSTK As Trade_In,
    b.VDSTK As Sold_Unit,
    b.VDSALA||b.VDSALC As Sale_Acc,
    Sold_Type,
    CBSMN As Salesperson,
    a.VDARA||a.VDARC As Current_Over_Acc,
    OA_ACC||substring(b.VDSALC,2,2) As Correct_Over_Acc
from CGIIND as a
    inner join CGIINH on a.VDCO||a.VDDIV||a.VDBR||a.VDINV = VHCO||VHDIV||VHBR||VHINV
    left join Sales as b on a.VDCO||a.VDDIV||a.VDBR||a.VDINV||a.VDLIN = b.VDCO||b.VDDIV||b.VDBR||b.VDINV||b.VDLIN
    left join OverMapping on substring(b.VDSALC,1,1)||CBTYP = OA_ID
where
    a.VDTYP in ('T') and a.VDARA <> '' and a.VDARA||a.VDARC <> OA_ACC||substring(b.VDSALC,2,2)
    and (
        VHSTA in ('R','P')
        or VHSTA = 'I' and VHDTI >= INTEGER(TO_CHAR(CURRENT DATE - 30 DAYS, 'YYYYMMDD'))
    );

-- update CGIIND
update CGIIND as a
set
   VDARA = 
        (select substring(Correct_Over_Acc,1,5)
        from DMOVRACCF as b
        where a.VDCO||a.VDDIV||a.VDBR||a.VDINV||a.VDLIN||a.VDTYP||a.VDSEQ = b.Trade_Key),
   VDARC =
        (select substring(Correct_Over_Acc,6,3)
        from DMOVRACCF as b
        where a.VDCO||a.VDDIV||a.VDBR||a.VDINV||a.VDLIN||a.VDTYP||a.VDSEQ = b.Trade_Key)
where
   a.VDCO||a.VDDIV||a.VDBR||a.VDINV||a.VDLIN||a.VDTYP||a.VDSEQ in
        (select Trade_Key from DMOVRACCF where STATUS <> 'Invoiced')