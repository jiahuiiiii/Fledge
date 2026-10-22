-- A first-login answer for people who don't know which companies to look at yet.
ALTER TABLE investor_profiles DROP CONSTRAINT investor_profiles_goal_check;
ALTER TABLE investor_profiles ADD CONSTRAINT investor_profiles_goal_check
 CHECK(goal IN ('learn','check','monitor','news','explore'));
