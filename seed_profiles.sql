INSERT INTO profiles (username, nombre, is_admin, pagado) VALUES
('messi10',      'Messi10',      false, false),
('ronaldo7',     'Ronaldo7',     false, false),
('mbappe9',      'Mbappe9',      false, false),
('neymar11',     'Neymar11',     false, false),
('haaland9',     'Haaland9',     false, false),
('vinicius7',    'Vinicius7',    false, false),
('bellingham8',  'Bellingham8',  false, false),
('pedri6',       'Pedri6',       false, false),
('salah11',      'Salah11',      false, false),
('ochoa',        'Ochoa',        false, false),
('modric10',     'Modric10',     false, false),
('debruyne17',   'DeBruyne17',   false, false),
('admin',        'Admin',        true,  false)
ON CONFLICT (username) DO NOTHING;
