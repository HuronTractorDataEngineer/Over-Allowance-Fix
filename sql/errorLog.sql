With

SettleMapping(SA_Key, Name, Email) AS (
  VALUES
    ('01','Laurie','lrussell@hurontractor.com'),
    ('02','Mel','mfinlayson@hurontractor.com'),
    ('03','Mel','mfinlayson@hurontractor.com'),
    ('04','Shelley','sbedard@hurontractor.com'),
    ('05','Mel','mfinlayson@hurontractor.com'),
    ('06','Mel','mfinlayson@hurontractor.com'),
    ('07','Shelley','sbedard@hurontractor.com'),
    ('08','LaurieP','lrussell@hurontractor.com'),
    ('10','Laurie','lrussell@hurontractor.com'),
    ('11','Laurie','lrussell@hurontractor.com'),
    ('19','Mel','mfinlayson@hurontractor.com'),
    ('DW','Shelley','sbedard@hurontractor.com'),
    ('092','Mel','mfinlayson@hurontractor.com')
    )

select
    a.*, Name, Email
from DMOVRACCF as a
    left join SettleMapping on case when Salesperson in ('092','DW') then Salesperson else Branch end = SA_Key