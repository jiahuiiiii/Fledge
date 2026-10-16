-- Lighter first login: a "keep up with news" goal, and the holding period is
-- no longer asked up front (it is derived from the trading-style answer).
ALTER TABLE investor_profiles DROP CONSTRAINT investor_profiles_goal_check;
ALTER TABLE investor_profiles ADD CONSTRAINT investor_profiles_goal_check
 CHECK(goal IN ('learn','check','monitor','news'));
