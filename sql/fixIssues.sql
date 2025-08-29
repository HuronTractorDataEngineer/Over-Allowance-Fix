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