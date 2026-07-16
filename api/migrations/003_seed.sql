insert into users (email, display_name) values ('help.sahil.gob@gmail.com', 'Sahil') on conflict do nothing;
insert into settings (user_id, plan_day_anchor)
  select id, date '2026-07-15' from users where email = 'help.sahil.gob@gmail.com'
on conflict do nothing;
