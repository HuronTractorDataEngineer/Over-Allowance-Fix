insert into DMOVRACCF
With

Sales As (
    select VDCO, VDDIV, VDBR, VDINV, VDLIN, VDSTK, VDSALA, VDSALC, CBTYP
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
    VHSTA As Status,
    a.VDBR As Branch,
    a.VDINV As Invoice,
    a.VDLIN As Line, 
    a.VDSTK As Trade_In,
    a.VDARA||a.VDARC As Current_Over_Acc,
    b.VDSTK As Sold_Unit,
    b.VDSALA||b.VDSALC As Sale_Acc,
    Sold_Type,
    OA_ACC||substring(b.VDSALC,2,2) As Correct_Over_Acc
from CGIIND as a
    inner join CGIINH on a.VDCO||a.VDDIV||a.VDBR||a.VDINV = VHCO||VHDIV||VHBR||VHINV
    left join Sales as b on a.VDCO||a.VDDIV||a.VDBR||a.VDINV||a.VDLIN = b.VDCO||b.VDDIV||b.VDBR||b.VDINV||b.VDLIN
    left join OverMapping on substring(b.VDSALC,1,1)||CBTYP = OA_ID
where
    VHSTA in ('R','P') and a.VDTYP in ('T') and a.VDARA <> '' and a.VDARA||a.VDARC <> OA_ACC||substring(b.VDSALC,2,2)