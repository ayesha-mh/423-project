

def draw_hud():
    now = glutGet(GLUT_ELAPSED_TIME)
    remaining = match_ms - (now - match_start_ms)
    draw_text(10, WINDOW_HEIGHT-28, f"Time: {max(0, remaining//1000)}s")
    draw_text(10, WINDOW_HEIGHT-52, f"Score You {player_score} : {ai_score} AI")
    draw_text(10, WINDOW_HEIGHT-76, "Kick: SPACE/LeftClick | Move: WASD | RightClick: FPP | T: TopDown | R: Restart")

    GG3D_SprintEnergy('draw', draw_text=draw_text, x=10, y=WINDOW_HEIGHT-100)
    GG3D_Penalty('draw_hud', draw_text=draw_text, x=10, y=80)

    if game_over:
        winner = "You Win!" if player_score > ai_score else ("Draw!" if player_score == ai_score else "AI Wins!")
        draw_text(WINDOW_WIDTH//2 - 60, WINDOW_HEIGHT//2 + 20, "GAME OVER")
        draw_text(WINDOW_WIDTH//2 - 60, WINDOW_HEIGHT//2 - 4, winner)
        draw_text(WINDOW_WIDTH//2 - 120, WINDOW_HEIGHT//2 - 28, "Press R to Restart")
    
def update_goalkeeper_xy(p, ball): 
   

    -
    goal_y = -GRID_LENGTH + 60.0
    x_min  = -GOAL_MOUTH * 0.5
    x_max  =  GOAL_MOUTH * 0.5
    slide_limit = GOAL_MOUTH * 0.45  
   -
    phase = p.get('gk_phase', 0.0)
    phase += 0.06                       
    if phase > (math.pi * 2.0):
        phase -= math.pi * 2.0
    p['gk_phase'] = phase

    
    PATROL_AMPL = slide_limit * 0.75    
    patrol_x    = math.sin(phase) * PATROL_AMPL

   
    inbound = (ball['vy'] > 0.25) and (ball['y'] < 0.0)
    if inbound:
        target_x = patrol_x * 0.5 + clamp(ball['x'], -slide_limit, slide_limit) * 0.5
    else:
        target_x = patrol_x

   
    target_x = clamp(target_x, -slide_limit, slide_limit)

   
    EASE      = 0.18
    MAX_STEP  = 0.65
    step_x    = (target_x - p['x']) * EASE
    if abs(step_x) > MAX_STEP:
        step_x = MAX_STEP if step_x > 0 else -MAX_STEP

    p['x'] = clamp(p['x'] + step_x, x_min, x_max)
    p['y'] = goal_y  

   
    dx, dy = ball['x'] - p['x'], ball['y'] - p['y']
    if dx*dx + dy*dy > 1e-6:
        p['angle'] = math.degrees(math.atan2(dy, dx)) - 90

def GG3D_Penalty(cmd=None, **kw):
   
    S = GG3D_Penalty.__dict__.setdefault('_S', {
        'active': False, 'waiting': False, 'frame': 0,
        'spot': (0.0, GRID_LENGTH - 180.0),       
        'goal': (0.0, GRID_LENGTH - 60.0),       
        'shooter_id': None, 'keeper_id': None,
        'label': None, 'label_timer': 0,
        # penalty-specific anim state
        'aim_phase': 0.0, 'aim_x': 0.0,           
    })

    def _unit(x, y):
        m = math.hypot(x, y)
        return (x/m, y/m) if m > 1e-8 else (0.0, 0.0)

    if cmd == 'active':
        return S['active']

    if cmd == 'end':
        S['active'] = False; S['waiting'] = False
        S['label'] = None;   S['label_timer'] = 0
        return

  
    if cmd == 'start'
        ball    = kw['ball']
        shooter = kw.get('shooter')    
        keeper  = kw.get('keeper')      
        bx, by = 0.0, GRID_LENGTH - 180.0
        gx, gy = 0.0, GRID_LENGTH - 60.0
        S['spot'], S['goal'] = (bx, by), (gx, gy)

     
        ball['x'], ball['y'] = bx, by
        ball['vx'], ball['vy'] = 0.0, 0.0

       
        if shooter and not shooter.get('is_keeper', False):
            shooter['x'] = bx
            shooter['y'] = by - 28.0
            shooter['angle'] = math.degrees(math.atan2(gy - shooter['y'], gx - shooter['x'])) - 90
            S['shooter_id'] = id(shooter)
        else:
            S['shooter_id'] = None

      
        if keeper:
            keeper['x'] = 0.0
            keeper['y'] = gy
            keeper['angle'] = math.degrees(math.atan2(by - keeper['y'], bx - keeper['x'])) - 90
            S['keeper_id'] = id(keeper)
        else:
            S['keeper_id'] = None

        # reset anim
        S['aim_phase'] = 0.0
        S['aim_x']     = bx

        S['active'] = True
        S['waiting'] = True
        S['frame'] = 0
        S['label'] = "PENALTY: Tap SPACE to shoot"
        S['label_timer'] = 120
        return

   
    if cmd == 'shoot':
        if not S['active'] or not S['waiting']:
            return
        ball = kw['ball']
        bx, by = S['spot']; gx, gy = S['goal']

      
        aim_x = S.get('aim_x', gx)
        ux, uy = _unit(aim_x - bx, gy - by)

        SHOT_SPEED = 16.0
        ball['x'], ball['y'] = bx, by
        ball['vx'], ball['vy'] = ux * SHOT_SPEED, uy * SHOT_SPEED
        cap_ball_speed()

        S['waiting'] = False
        S['label'] = "Shot taken"
        S['label_timer'] = 50
        return

   
    if cmd == 'update':
        ball = kw['ball']
        mt = kw.get('my_team', globals().get('my_team', []))
        et = kw.get('enemies',  globals().get('enemies', []))
        if not S['active']:
            return False

        S['frame'] += 1
        bx, by = S['spot']; gx, gy = S['goal']

       
        shooter = next((p for p in mt if id(p) == S['shooter_id']), None)
        if S['waiting'] and shooter:
            sway_limit = min(GOAL_MOUTH * 0.45, 80.0)
            S['aim_phase'] = (S['aim_phase'] + 0.055) % (math.pi * 2.0)
            target_x = bx + math.sin(S['aim_phase']) * sway_limit   
            S['aim_x'] = clamp(target_x, bx - sway_limit, bx + sway_limit)

           
            ease = 0.20
            max_step = 0.9
            dxs = (S['aim_x'] - shooter['x']) * ease
            if abs(dxs) > max_step: dxs = max_step if dxs > 0 else -max_step
            shooter['x'] = clamp(shooter['x'] + dxs, bx - sway_limit, bx + sway_limit)
            shooter['y'] = by - 28.0 
            shooter['angle'] = math.degrees(math.atan2(gy - shooter['y'], gx - shooter['x'])) - 90

          
            ball['x'], ball['y'] = bx, by
            ball['vx'], ball['vy'] = 0.0, 0.0

        
        keeper = next((p for p in et if id(p) == S['keeper_id']), None)
        if keeper:
            mouth = GOAL_MOUTH * 0.45
           
            patrol = math.sin(S['frame'] * 0.045) * (mouth * 0.65)
            if S['waiting']:
                target_x = 0.6 * patrol + 0.4 * clamp(S['aim_x'], -mouth, mouth)
            else:
                target_x = clamp(ball['x'], -mouth, mouth) 
            dist_to_line = max(0.0, gy - ball['y'])
            target_y = gy - min(24.0, dist_to_line * 0.25)

         
            ease_x, ease_y = 0.18, 0.14
            max_step = 0.85
            dxk = (target_x - keeper['x']) * ease_x
            dyk = (target_y - keeper['y']) * ease_y
            step_len = math.hypot(dxk, dyk)
            if step_len > max_step:
                uxk, uyk = _unit(dxk, dyk)
                dxk, dyk = uxk * max_step, uyk * max_step

            keeper['x'] = clamp(keeper['x'] + dxk, -mouth, mouth)
            keeper['y'] = clamp(keeper['y'] + dyk, gy - 24.0, gy)

           
            fx, fy = ball['x'] - keeper['x'], ball['y'] - keeper['y']
            if fx*fx + fy*fy > 1e-6:
                keeper['angle'] = math.degrees(math.atan2(fy, fx)) - 90

          
            if not S['waiting']:
                if math.hypot(fx, fy) < (BODY_WIDTH * 0.8 + BALL_RADIUS):
                    ball['vy'] = -abs(ball['vy']) * 0.6
                    ball['vx'] *= 0.6
                    cap_ball_speed()
                    S['label'] = "SAVE!"
                    S['label_timer'] = 50
                    S['active'] = False
                    S['waiting'] = False

        
        if abs(ball['y']) > GRID_LENGTH - 10.0:
            S['active'] = False; S['waiting'] = False

        if S['label_timer'] > 0:
            S['label_timer'] -= 1
        return True

   
    if cmd == 'draw_hud':
        draw_text = kw.get('draw_text')
        x = kw.get('x', 10); y = kw.get('y', 80)
        if not draw_text: return
        if S['active']:
            msg = S['label'] if (S['label'] and S['label_timer'] > 0) else "PENALTY"
            draw_text(x, y, msg)


def idle_update():
    global game_over
    GG3D_SprintEnergy('tick')
    if GG3D_Penalty('active'):
        GG3D_Penalty('update', ball=ball, my_team=my_team, enemies=enemies)
        update_ball()
        glutPostRedisplay()
        glutTimerFunc(16, lambda t=0: idle_update(), 0)
        return

    if not game_over:
        enemy_ai_update()
        my_team_update()
        update_ball()

        for p in my_team:
            if p.get('is_user', False):
                p['x'] = player_x
                p['y'] = player_y
                p['angle'] = player_angle

        now = glutGet(GLUT_ELAPSED_TIME)
        remaining = match_ms - (now - match_start_ms)
        if remaining <= 0:
            game_over = True

    glutPostRedisplay()
    glutTimerFunc(16, lambda t=0: idle_update(), 0)


def GG3D_SprintEnergy(cmd=None, **kw):
    S = GG3D_SprintEnergy.__dict__.setdefault('_S', {
        'energy': 100.0,
        'sprinting': False,
        'SPRINT_MULT': 1.6,
        'DRAIN_RATE': 0.35,
        'REGEN_RATE': 0.18,
        'MIN_TO_SPRINT': 1.0,
    })

    def _clamp01(v): 
        return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)

    if cmd == 'maybe_scale':
        want = bool(kw.get('want_sprint', False))
        can  = (S['energy'] > S['MIN_TO_SPRINT'])
        S['sprinting'] = (want and can)
        return S['SPRINT_MULT'] if S['sprinting'] else 1.0

    if cmd == 'tick':
        if S['sprinting']:
            S['energy'] -= S['DRAIN_RATE']
        else:
            S['energy'] += S['REGEN_RATE']
        if S['energy'] <= 0.0:
            S['energy'] = 0.0
            S['sprinting'] = False
        elif S['energy'] > 100.0:
            S['energy'] = 100.0
        return

    if cmd == 'draw':
        draw_text = kw.get('draw_text')
        if not draw_text:
            return
        x = kw.get('x', 10)
        y = kw.get('y', 80)
        e = int(round(S['energy']))
        slots = 20
        filled = int(round(_clamp01(S['energy']/100.0) * slots))
        bar = "[" + ("|"*filled) + ("."*(slots - filled)) + "]"
        draw_text(x, y,      f"Energy: {e}")
        draw_text(x, y - 20, bar)
        return

    if cmd == 'state':
        return dict(S)



def keyboardListener(key, x, y):
    global player_x, player_y, player_angle, game_over, player_score, ai_score, match_start_ms, first_person, topdown_view
    move_step  = 10 * PLAYER_SCALE
    angle_step = 6

    raw = key.decode("utf-8")
    k   = raw.lower()

    if k == 'p':
        shooter = next((pp for pp in my_team if pp.get('is_user', False) and not pp.get('is_keeper', False)), None)
        if shooter is None:
            fielders = [pp for pp in my_team if not pp.get('is_keeper', False)]
            shooter = fielders[0] if fielders else (my_team[0] if my_team else None)
        opp_keeper = next((pp for pp in enemies if pp.get('is_keeper', False)), None)
        if opp_keeper is None and enemies:
            opp_keeper = enemies[0]
        if shooter is not None and opp_keeper is not None:
            GG3D_Penalty('start', ball=ball, shooter=shooter, keeper=opp_keeper)
        glutPostRedisplay()
        return

    if GG3D_Penalty('active'):
        if k == ' ':
            GG3D_Penalty('shoot', ball=ball)
            glutPostRedisplay()
            return
        if k in ('w','a','s','d','q','e'):
            glutPostRedisplay()
            return

    if k == '\x1b':
        try: glutLeaveMainLoop()
        except: pass
        return

    if k == 'r' and game_over:
        player_score = 0; ai_score = 0
        reset_ball(); init_teams()
        game_over = False
        match_start_ms = glutGet(GLUT_ELAPSED_TIME)
        return

    if game_over: return

    _sprint_now = raw.isalpha() and raw.isupper()

    if k == 't':
        topdown_view = not topdown_view
    elif k == 'c':
        pass
    elif k == 'w':
        mult = GG3D_SprintEnergy('maybe_scale', want_sprint=_sprint_now)
        rad = math.radians(player_angle + 90)
        player_x += math.cos(rad) * move_step * mult
        player_y += math.sin(rad) * move_step * mult
        maybe_dribble_push(True)
    elif k == 's':
        mult = GG3D_SprintEnergy('maybe_scale', want_sprint=_sprint_now)
        rad = math.radians(player_angle + 90)
        player_x -= math.cos(rad) * move_step * mult
        player_y -= math.sin(rad) * move_step * mult
    elif k == 'a':
        player_angle += angle_step
    elif k == 'd':
        player_angle -= angle_step
    elif k == 'q':
        mult = GG3D_SprintEnergy('maybe_scale', want_sprint=_sprint_now)
        rad = math.radians(player_angle)
        player_x += math.cos(rad) * (-move_step * mult)
        player_y += math.sin(rad) * (-move_step * mult)
    elif k == 'e':
        mult = GG3D_SprintEnergy('maybe_scale', want_sprint=_sprint_now)
        rad = math.radians(player_angle)
        player_x += math.cos(rad) * (move_step * mult)
        player_y += math.sin(rad) * (move_step * mult)
    elif k == ' ':
        try_kick(True)

    player_x_clamped = clamp(player_x, -GRID_LENGTH, GRID_LENGTH)
    player_y_clamped = clamp(player_y, -GRID_LENGTH, GRID_LENGTH)
    for p in my_team:
        if p.get('is_user', False):
            p['x'], p['y'] = player_x_clamped, player_y_clamped
            p['angle'] = player_angle
    globals()['player_x'] = player_x_clamped
    globals()['player_y'] = player_y_clamped
    glutPostRedisplay()




