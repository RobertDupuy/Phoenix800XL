# One eight-pixel row above the previous port position. Arcade paths continue
# to use their original world coordinates; the player's entire footprint moves.
.set player_raise,8
.set player_raw_y,216-player_raise
.set player_pm_y,224-player_raise
.set player_shot_y,208-player_raise
.set player_body_min_y,210-player_raise
.set player_body_max_y,231-player_raise
.set player_bomb_min_y,220-player_raise
.set player_bomb_max_y,233-player_raise
.set player_shield_raw_y,208-player_raise
.set player_shield_pm_y,216-player_raise
.set player_shield_row,22-player_raise/8
.set player_shield_body_min_y,202-player_raise
.set player_shield_body_max_y,239-player_raise
.set player_shield_bomb_y,212-player_raise
.set player_explosion_row,12-player_raise/8
.set escort_population,5
.set large_population,7
.set escort_fast_threshold,3
.set dark_blue_stars,0x82
.set safe_entry_events,0x7eb

