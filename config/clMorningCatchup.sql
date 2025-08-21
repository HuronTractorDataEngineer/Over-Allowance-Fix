With

Open_Work As (
    select
        WHSTK,
        count(*) Open_WOS,
        listagg(WRBR||'-'||WRORD,', ') WO_List
    from WOR
        inner join WOH on WRCO||WRDIV||WRBR||WRORD = WHCO||WHDIV||WHBR||WHORD
    where WRCO = '01' and WRDIV = '01' and WRSTA <> 'D' and WHSTA = 'A' and WRREP = 1
        and WHTID not in (select HHTID from INVHH)
        and WHSTK <> '?'
    group by WHSTK
    ),
    
Departments(Dept_Code, Department) AS (
  VALUES
    ('0', 'B/S'),
    ('1', 'ADMIN'),
    ('2', 'AG'),
    ('3', 'AMS'),
    ('4', 'SERVICE'),
    ('5', 'TURF'),
    ('6', 'CCE'),
    ('7', 'CRARY')
    ),
    
Unit_Status (Sta_Key, Status) As (
    values
        ('V','Inventory'),
        ('R','Rental'),
        ('S','Sold'),
        ('O','On Order'),
        ('Q','Quoted'),
        ('P','Pre-Sold'),
        ('D','Deleted'),
        ('T','Transfered'),
        ('I','Invoiced'),
        ('X','In Use')
        ),
        
Branches As (
    SELECT TBCO||TBDIV||TBBR As Br_Key,
      TRIM(SUBSTR(TBDATA, 1, 15)) AS Branch
    FROM PFWTAB WHERE TBFILE = 'CMBR' and TBSTA = ''
    ),

CorpSM(SM_ID, SM_BR) AS (
  VALUES
    ('100', 'Corporate'),
    ('200', 'Corporate'),
    ('500', 'Corporate'),
    ('532', 'Corporate'),
    ('092', 'Corporate')
    ),

--Sales people names        
Sales_Person As (
    SELECT TBCO||TBDIV||TRIM(SUBSTR(TBKEY, 13, 3)) As SM_Key,
      TRIM(SUBSTR(TBDATA, 1, 25)) AS SM_Name,
      case when SM_ID is not null then SM_BR else Branch end As SM_BR
    FROM PFWTAB
        left join CorpSM on TRIM(SUBSTR(TBKEY, 13, 3)) = SM_ID
        left join Branches on TBCO||TBDIV||SUBSTR(TBDATA, 26, 2) = Br_Key
    WHERE TBFILE = 'CMSMN'
    ORDER BY TBCO||TBDIV||RTRIM(SUBSTR(TBKEY, 13, 3))
    ),

Sales_Emails As (
    select WUSPR, trim(WUEML) As WUEML
    from WEBUSR
            left join USRPRF1067 on WUUID = USRPRF
    where WUSPR <> '' --between '000' and '999'--in (select distinct CBSMN from CGIBASE where CBSMN <> '')
        and WUUNM not like '%CDK%'
        and right(RTRIM(WUUID),2) between '00' and '99'
        and WUUID <> 'CR1067'
        and upper(trim(WUEML)) not like '%@CDK.COM'
        and STATUS <> '*DISABLED '
        ),
        
Filtered As (
    select *
    from LOGCGIB
    where CBCO = '01' and CBDIV = '01' and CBSTA <> 'X' and CBTYPE in ('B','A')
    )
    
,Numbered As (
    select
        row_number() over (partition by CBORD order by CB_DATE, CB_TIME) As rn
        ,a.*
    from Filtered as a
    )

,Dataset As (
    select
        a.CBUSER
        ,a.CBJOB
        ,a.CBDATE
        ,a.CBTIME
        ,a.CBCO
        ,a.CBDIV
        ,a.CBORD
        ,a.CBMAK
        ,a.CBMOD
        ,a.CBDES
        ,a.CBTYP
        ,a.CBGRP
        ,a.CBGLSC
        ,a.CBSMN
        ,a.CBSUB
        ,a.CBOTH
        ,trim(a.CBBIN) As CBPUR
        ,a.CBCUS
        ,b.CBSTA As b_Sta
        ,a.CBSTA As a_Sta
        ,b.CBBR As b_Br
        ,a.CBBR As a_Br
    from Numbered as b
        join Numbered as a on b.CBORD = a.CBORD and b.rn+1 = a.rn
    where b.CBTYPE = 'B' and a.CBTYPE = 'A'
        and (
            b.CBSTA <> a.CBSTA
            or b.CBBR <> a.CBBR
            )
    )

,StatusBranchChangeLog As (
    select
        CBUSER As User_ID,
        CBJOB As Job,
        DATE(TIMESTAMP_FORMAT(CBDATE,'YYYYMMDD')) As Event_Date,
        TIMESTAMP_FORMAT(
            CBDATE || LPAD(CBTIME ,6,'0'),
            'YYYYMMDDHH24MISS'
        )  AS Event_TS,
        CBORD As Stock_Number,
        CBMAK As Make,
        CBMOD As Model,
        CBDES As Description,
        case when CBTYP = 'N' then 'New' else 'Used' end As Type,
        CBGRP As Group_Code,
        Department,
        sp.SM_Name As Salesperson,
        se.WUEML As Salesperson_Email,
        pp.SM_Name As Purchaser,
        pe.WUEML As Purchaser_Email,
        CUCUS As Customer,
        CUNME As Name,
        CBSUB+CBOTH As Retail,
        case
            when b_Sta <> a_Sta and b_Br = a_Br then 'Status'
            when b_Sta = a_Sta and b_Br <> a_Br then 'Branch'
            else 'Sta and Br' end As Change_Type,
        case when b_Sta <> a_Sta then bst.Status||' to '||ast.Status else '' end As Status_Change,
        ast.Status As Status,
        case when b_Br <> a_Br then bb.Branch||' to '||ab.Branch else '' end As Branch_Change,
        bb.Branch As Previous_Branch,
        ab.Branch As Current_Branch,
        Open_WOS,
        WO_List
    from Dataset as a
        left join Branches as bb on CBCO||CBDIV||B_Br = bb.Br_Key
        left join Branches as ab on CBCO||CBDIV||A_Br = ab.Br_Key
        left join Unit_Status as bst on B_Sta = bst.Sta_Key
        left join Unit_Status as ast on A_Sta = ast.Sta_Key
        left join Sales_Person sp on CBCO||CBDIV||CBSMN = sp.SM_Key
        left join Sales_Person pp on CBCO||CBDIV||CBPUR = pp.SM_Key
        left join Sales_Emails as se on CBSMN = se.WUSPR
        left join Sales_Emails as pe on CBPUR = pe.WUSPR
        left join Departments on substring(CBGLSC,1,1) = Dept_Code
        left join CMASTR on CBCO||CBDIV||CBCUS = CUCO||CUDIV||CUCUS
        left join Open_Work on CBORD = WHSTK
    where CBDATE >= INTEGER(VARCHAR_FORMAT(current date - 7 days, 'YYYYMMDD'))
    )
    
    select *
    from StatusBranchChangeLog
    where
        Event_TS >= (TIMESTAMP_FORMAT(VARCHAR_FORMAT(CURRENT TIMESTAMP, 'YYYY-MM-DD-HH24') || ':30:00','YYYY-MM-DD-HH24:MI:SS') - 17 HOUR)
        and Event_TS <  TIMESTAMP_FORMAT(VARCHAR_FORMAT(CURRENT TIMESTAMP, 'YYYY-MM-DD-HH24') || ':00:00','YYYY-MM-DD-HH24:MI:SS')
    order by Event_TS desc