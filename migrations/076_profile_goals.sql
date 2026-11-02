-- First-login question 2 allows several answers. `goal` stays as the first
-- pick (older code and the investor-type score read it); `goals` holds them all.
ALTER TABLE investor_profiles ADD COLUMN goals text[] NOT NULL DEFAULT '{}';
UPDATE investor_profiles SET goals=ARRAY[goal];
ALTER TABLE investor_profiles ADD CONSTRAINT investor_profiles_goals_check
 CHECK(goals <@ ARRAY['learn','check','monitor','news','explore']::text[]);
