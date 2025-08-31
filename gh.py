
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, random

# --------------------------
# Basic window / camera vars
# --------------------------
fovY = 60
GRID_LENGTH = 600
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800

# air physics (tiny arc)
GRAVITY_Z      = -0.5
BOUNCE_Z       = 0.40
AIR_DRAG       = 0.995
FLY_LIFT_SMALL = 9.5
LONG_SHOT_LIFT = 8.0

LONG_SHOT_MSG_MS = 700
long_shot_msg_until = -1
def spawn_ball_at_user_feet(offset=20.0, lock_ms=1200):
    """Puts the ball just ahead of the user-controlled player and gives them possession."""
    user = next((pp for pp in my_team if pp.get('is_user', False)), None)
    if user is None:
        return
    ball['x'] = user['x']
    ball['y'] = user['y'] + offset
    ball['z'] = BALL_RADIUS
    ball['vx'] = 0.0
    ball['vy'] = 0.0
    ball['vz'] = 0.0
    GG3D_Possession('set', player=user, duration_ms=lock_ms)

# --------------------------
# AFSANA ADD-ON: Celebration / Weather / Replay Camera state
# --------------------------
iscelebrating = False
animationlimbingles = {'left_arm': 0, 'right_arm': 0, 'left_leg': 0, 'right_leg': 0}

isday = True
israining = False
RAINPARTICLES = 150
rainpositions = []
weatherinitialized = False

isinreplay = False
replaytimer = 0
replaycameraangle = 1

celebrationtimer = 0
MAXCELEBRATIONTIME = 300
animationphase = 0.0

def getcolorformode(daycolor, nightcolor):
    return daycolor if isday else nightcolor

def initweather():
    global rainpositions, weatherinitialized
    if not weatherinitialized:
        for _ in range(RAINPARTICLES):
            x = random.uniform(-GRID_LENGTH, GRID_LENGTH)
            y = random.uniform(-GRID_LENGTH, GRID_LENGTH)
            z = random.uniform(80.0, 320.0)
            rainpositions.append([x, y, z])
        weatherinitialized = True

def weather(command):
    global isday, israining
    if command == 'draw' and israining:
        glEnable(GL_LINE_SMOOTH)
        glLineWidth(1.2)
        glColor3f(0.7, 0.8, 0.9)
        glBegin(GL_LINES)
        for x, y, z in rainpositions:
            glVertex3f(x, y, z)
            glVertex3f(x, y, z - 6.0)
        glEnd()
    elif command == 'update' and israining:
        for i in range(len(rainpositions)):
            rainpositions[i][2] -= 5.0
            if rainpositions[i][2] < 0.0:
                rainpositions[i][0] = random.uniform(-GRID_LENGTH, GRID_LENGTH)
                rainpositions[i][1] = random.uniform(-GRID_LENGTH, GRID_LENGTH)
                rainpositions[i][2] = 320.0
    elif command == 'toggle_day_night':
        isday = not isday
    elif command == 'toggle_rain':
        israining = not israining

def celebration(command, limbanglesin=None):
    global celebrationtimer, animationphase
    limbanglesout = limbanglesin if limbanglesin is not None else {}
    if command == 'start':
        celebrationtimer = MAXCELEBRATIONTIME
        animationphase = 0.0
        return True
    elif command == 'update':
        if celebrationtimer > 0:
            celebrationtimer -= 1
            animationphase += 0.20
            swing = math.sin(animationphase) * 55.0
            limbanglesout.update({
                'left_arm':  swing,
                'right_arm': -swing,
                'left_leg':  -swing,
                'right_leg': swing
            })
            return True, limbanglesout
        else:
            limbanglesout = {k: 0 for k in limbanglesout}
            return False, limbanglesout

def setreplaycamera():
    if replaycameraangle == 1:
        # behind the ball toward the goal
        gluLookAt(ball['x'], ball['y'] - 50, 20, ball['x'], ball['y'], ball['z'], 0, 0, 1)
    elif replaycameraangle == 2:
        # side view near player
        gluLookAt(player_x + 100, player_y, 50, player_x, player_y, 50, 0, 0, 1)
    elif replaycameraangle == 3:
        # high top-down
        gluLookAt(0, 0, 800, 0, 0, 0, 0, 1, 0)

# --------------------------
# HUD text
# --------------------------
def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18):
    glColor3f(1,1,1)
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, WINDOW_WIDTH, 0, WINDOW_HEIGHT)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)

# --------------------------
# Gameplay constants & state
# --------------------------
PLAYER_SCALE = 0.3
BODY_HEIGHT = 50 * PLAYER_SCALE
BODY_WIDTH  = 50 * 1.2 * PLAYER_SCALE
HEAD_RADIUS = 50 * 0.5 * PLAYER_SCALE
LIMB_RADIUS = 50 * 0.15 * PLAYER_SCALE
LEG_LENGTH  = 50 * 1.5 * PLAYER_SCALE
ARM_LENGTH  = 50 * 1.2 * PLAYER_SCALE

# User controller mirror of current user-controlled teammate
player_x = 0.0
player_y = -GRID_LENGTH * 0.35
player_angle = 0.0  # 0 faces +Y

# Ball
BALL_RADIUS = max(50 * 0.35 * PLAYER_SCALE, 4.5)
ball = {'x': 0.0, 'y': 0.0, 'z': BALL_RADIUS, 'vx': 0.0, 'vy': 0.0, 'vz': 0.0}
BALL_FRICTION = 0.985
BALL_MAX_SPEED = 30.0
KICK_POWER = 28.0
DRIBBLE_PUSH = 2.5
KICK_REACH = (BODY_WIDTH * 1.1) + 6.0

# Dribble tuning to prevent over-push
DRIBBLE_MIN_GAP = 7.0   # if ball is closer than this to your footprint, don't push
DRIBBLE_MAX_SPEED = 7.0 # cap ball speed while dribbling nudges

# Goals and scoring
GOAL_MOUTH = GRID_LENGTH * 0.6
GOAL_TARGET_TOP = (0.0, GRID_LENGTH + 50.0)
GOAL_TARGET_BOTTOM = (0.0, -GRID_LENGTH - 50.0)
player_score = 0
ai_score = 0

# Timer
match_ms = 90_000
match_start_ms = None
game_over = False

# Camera modes
first_person = False
topdown_view = False
camera_angle = 45
camera_height = 600
camera_radius = 800

# AI & teams
ENEMY_KICK = 22.0
ENEMY_BASE_DETECT = 220.0

enemies = []
my_team = []

# --------------------------
# Helpers
# --------------------------
def clamp(v, lo, hi): return max(lo, min(hi, v))
def dist2d(ax, ay, bx, by): return math.hypot(ax-bx, ay-by)
def unit_vec(dx, dy):
    d = math.hypot(dx, dy)
    return (0.0, 0.0) if d < 1e-8 else (dx/d, dy/d)

def cap_ball_speed(limit=None):
    lim = BALL_MAX_SPEED if limit is None else limit
    sp = math.hypot(ball['vx'], ball['vy'])
    if sp > lim:
        s = lim / max(sp, 1e-8)
        ball['vx'] *= s; ball['vy'] *= s

def reset_ball(center=True):
    ball['x'] = 0.0 if center else random.uniform(-GRID_LENGTH*0.2, GRID_LENGTH*0.2)
    ball['y'] = 0.0 if center else random.uniform(-GRID_LENGTH*0.2, GRID_LENGTH*0.2)
    ball['vx'] = 0.0; ball['vy'] = 0.0; ball['vz'] = 0.0
    ball['z'] = BALL_RADIUS
    GG3D_Possession('clear')

def dist_point_to_segment(px, py, ax, ay, bx, by):
    """Return (distance, t in [0,1], closest_x, closest_y) from P to segment AB."""
    abx, aby = bx - ax, by - ay
    ab2 = abx*abx + aby*aby
    if ab2 <= 1e-9:
        dx, dy = px - ax, py - ay
        return (math.hypot(dx, dy), 0.0, ax, ay)
    t = ((px - ax)*abx + (py - ay)*aby) / ab2
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    cx, cy = ax + t*abx, ay + t*aby
    return (math.hypot(px - cx, py - cy), t, cx, cy)

def transfer_control_to(target):
    global player_x, player_y, player_angle
    cur = next((p for p in my_team if p.get('is_user', False)), None)
    if cur is not None:
        cur['is_user'] = False
    target['is_user'] = True
    player_x, player_y, player_angle = target['x'], target['y'], target['angle']

# --------------------------
# Possession lock manager (3s no-steal)
# --------------------------
def GG3D_Possession(cmd=None, **kw):
    S = GG3D_Possession.__dict__.setdefault('_S', {
        'holder_id': None,
        'until_ms': 0,
    })
    now = glutGet(GLUT_ELAPSED_TIME)

    if cmd == 'holder':
        return S['holder_id']

    if cmd == 'can_take':
        p = kw.get('player')
        if p is None: return True
        pid = id(p)
        return (S['holder_id'] is None) or (S['holder_id'] == pid) or (now >= S['until_ms'])

    if cmd == 'set':
        p = kw.get('player')
        dur = int(kw.get('duration_ms', 3000))
        S['holder_id'] = id(p) if p is not None else None
        S['until_ms']  = now + dur if p is not None else 0
        return

    if cmd == 'clear':
        S['holder_id'] = None
        S['until_ms']  = 0
        return

# --------------------------
# Sprint HUD
# --------------------------
def GG3D_SprintEnergy(cmd=None, **kw):
    S = GG3D_SprintEnergy.__dict__.setdefault('_S', {
        'energy': 100.0,
        'sprinting': False,
        'SPRINT_MULT': 1.6,
        'DRAIN_RATE': 0.35,
        'REGEN_RATE': 0.18,
        'MIN_TO_SPRINT': 1.0,
        'want': False,
    })
    def _clamp01(v): return 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)
    if cmd == 'maybe_scale':
        want = bool(kw.get('want_sprint', False))
        can  = (S['energy'] > S['MIN_TO_SPRINT'])
        S['want'] = (want and can)
        return S['SPRINT_MULT'] if S['want'] else 1.0
    if cmd == 'tick':
        if S['want']: S['sprinting'] = True; S['energy'] -= S['DRAIN_RATE']
        else:
            S['sprinting'] = False
            if S['energy'] < 100.0: S['energy'] += S['REGEN_RATE']
        if S['energy'] <= 0.0: S['energy'] = 0.0; S['sprinting'] = False
        if S['energy'] > 100.0: S['energy'] = 100.0
        S['want'] = False; return
    if cmd == 'draw':
        draw_text_fn = kw.get('draw_text')
        if not draw_text_fn: return
        x = kw.get('x', 10); y = kw.get('y', 80)
        e = int(round(S['energy'])); slots = 20
        filled = int(round(_clamp01(S['energy']/100.0) * slots))
        bar = "[" + ("|"*filled) + ("."*(slots - filled)) + "]"
        draw_text_fn(x, y,      f"Energy: {e}")
        draw_text_fn(x, y - 20, bar)
        return
    if cmd == 'state': return dict(S)

# --------------------------
# Penalty system (shooter vs keeper)
# --------------------------
def GG3D_Penalty(cmd=None, **kw):
    S = GG3D_Penalty.__dict__.setdefault('_S', {
        'active': False, 'waiting': False, 'frame': 0,
        'spot': (0.0, GRID_LENGTH - 180.0),
        'goal': (0.0, GRID_LENGTH - 60.0),
        'shooter_id': None, 'keeper_id': None,
        'label': None, 'label_timer': 0,
        'aim_phase': 0.0, 'aim_x': 0.0,
        'penalty_count': 0, 'max_penalties': 3,
    })
    def _unit(x, y):
        m = math.hypot(x, y)
        return (x/m, y/m) if m > 1e-8 else (0.0, 0.0)

    if cmd == 'active': return S['active']
    if cmd == 'end':
        S['active']=False; S['waiting']=False; S['label']=None; S['label_timer']=0; S['penalty_count']=0; return

    if cmd == 'start':
        b = kw['ball']; shooter = kw.get('shooter'); keeper = kw.get('keeper')
        GG3D_Possession('clear')
        if S['penalty_count'] >= S['max_penalties']: S['penalty_count']=0
        bx, by = 0.0, GRID_LENGTH - 180.0; gx, gy = 0.0, GRID_LENGTH - 60.0
        S['spot'], S['goal'] = (bx, by), (gx, gy)
        b['x'], b['y'] = bx, by; b['vx']=b['vy']=0.0; b['z']=BALL_RADIUS
        if shooter and not shooter.get('is_keeper', False):
            shooter['x']=bx; shooter['y']=by - 28.0
            shooter['angle']=math.degrees(math.atan2(gy - shooter['y'], gx - shooter['x'])) - 90
            S['shooter_id']=id(shooter)
        else: S['shooter_id']=None
        if keeper:
            keeper['x']=0.0; keeper['y']=gy
            keeper['angle']=math.degrees(math.atan2(by - keeper['y'], bx - keeper['x'])) - 90
            S['keeper_id']=id(keeper)
        else: S['keeper_id']=None
        S['aim_phase']=0.0; S['aim_x']=bx
        S['active']=True; S['waiting']=True; S['frame']=0
        S['label']=f"PENALTY {S['penalty_count']+1}/{S['max_penalties']}: Tap SPACE to shoot"; S['label_timer']=120
        return

    if cmd == 'shoot':
        if not S['active'] or not S['waiting']: return
        b = kw['ball']; bx, by = S['spot']; gx, gy = S['goal']
        aim_x = S.get('aim_x', gx)
        ux, uy = _unit(aim_x - bx, gy - by)
        SHOT_SPEED = 16.0
        b['x'], b['y'] = bx, by
        b['vx'], b['vy'] = ux * SHOT_SPEED, uy * SHOT_SPEED
        b['vz'] = 2.0
        S['waiting'] = False; S['label']="Shot taken"; S['label_timer']=50; return

    if cmd == 'update':
        b = kw['ball']; mt = kw.get('my_team', my_team); et = kw.get('enemies', enemies)
        if not S['active']: return False
        S['frame'] += 1
        bx, by = S['spot']; gx, gy = S['goal']

        shooter = next((p for p in mt if id(p) == S['shooter_id']), None)
        if S['waiting'] and shooter:
            sway_limit = min(GOAL_MOUTH * 0.45, 80.0)
            S['aim_phase'] = (S['aim_phase'] + 0.055) % (math.pi * 2.0)
            target_x = bx + math.sin(S['aim_phase']) * sway_limit
            S['aim_x'] = clamp(target_x, bx - sway_limit, bx + sway_limit)
            ease = 0.20; max_step = 0.9
            dxs = (S['aim_x'] - shooter['x']) * ease
            if abs(dxs) > max_step: dxs = max_step if dxs > 0 else -max_step
            shooter['x'] = clamp(shooter['x'] + dxs, bx - sway_limit, bx + sway_limit)
            shooter['y'] = by - 28.0
            shooter['angle'] = math.degrees(math.atan2(gy - shooter['y'], gx - shooter['x'])) - 90
            b['x'], b['y'] = bx, by; b['vx']=b['vy']=0.0; b['z']=BALL_RADIUS

        keeper = next((p for p in et if id(p) == S['keeper_id']), None)
        if keeper:
            mouth = GOAL_MOUTH * 0.45
            patrol = math.sin(S['frame'] * 0.045) * (mouth * 0.65)
            if S['waiting']:
                target_x = 0.6 * patrol + 0.4 * clamp(S['aim_x'], -mouth, mouth)
            else:
                target_x = clamp(b['x'], -mouth, mouth)
            dist_to_line = max(0.0, gy - b['y'])
            target_y = gy - min(24.0, dist_to_line * 0.25)
            ease_x, ease_y = 0.18, 0.14; max_step = 0.85
            dxk = (target_x - keeper['x']) * ease_x; dyk = (target_y - keeper['y']) * ease_y
            step_len = math.hypot(dxk, dyk)
            if step_len > max_step:
                uxk, uyk = (dxk/step_len, dyk/step_len); dxk, dyk = uxk * max_step, uyk * max_step
            keeper['x'] = clamp(keeper['x'] + dxk, -mouth, mouth)
            keeper['y'] = clamp(keeper['y'] + dyk, gy - 24.0, gy)
            fx, fy = b['x'] - keeper['x'], b['y'] - keeper['y']
            if fx*fx + fy*fy > 1e-6:
                keeper['angle'] = math.degrees(math.atan2(fy, fx)) - 90
            if not S['waiting']:
                if math.hypot(fx, fy) < (BODY_WIDTH * 0.8 + BALL_RADIUS):
                    b['vy'] = -abs(b['vy']) * 0.6; b['vx'] *= 0.6
                    cap_ball_speed()
                    S['label'] = "SAVE!"; S['label_timer'] = 50

        if not S['waiting'] and (abs(b['y']) > GRID_LENGTH - 10.0 or 
                                 (S['label'] == "SAVE!" and S['label_timer'] <= 0)):
            S['penalty_count'] += 1
            if S['penalty_count'] >= S['max_penalties']:
                S['active'] = False; S['waiting'] = False
                S['label'] = f"Penalty sequence complete: {S['penalty_count']}/{S['max_penalties']}"; S['label_timer']=100
            else:
                shooter = next((p for p in mt if id(p) == S['shooter_id']), None)
                keeper  = next((p for p in et if id(p) == S['keeper_id']), None)
                if shooter and keeper: GG3D_Penalty('start', ball=b, shooter=shooter, keeper=keeper)

        if S['label_timer'] > 0: S['label_timer'] -= 1
        return True

    if cmd == 'draw_hud':
        draw_text_fn = kw.get('draw_text'); x = kw.get('x', 10); y = kw.get('y', 80)
        if not draw_text_fn: return
        if S['active']:
            msg = S['label'] if (S['label'] and S['label_timer'] > 0) else f"PENALTY {S['penalty_count']+1}/{S['max_penalties']}"
            draw_text_fn(x, y, msg)
        return

# --------------------------
# Build teams & positions
# --------------------------
def _role_move_range(role):
    if role in ('GK','Keeper'): return 90.0
    if role == 'DEF': return 180.0
    if role == 'MID': return 240.0
    return 300.0

def add_enemy(role, hx, hy, color, detect_scale, speed):
    enemies.append({
        'role': role,
        'home_x': hx, 'home_y': hy,
        'x': hx, 'y': hy,
        'angle': 0.0,
        'color': color,
        'detect': ENEMY_BASE_DETECT * detect_scale,
        'speed': speed,
        'has_ball': False,
        'prev_has_ball': False,
        'force_return_frames': 0,
        'move_range': _role_move_range(role),
        'is_keeper': (role == 'GK')
    })

def add_my_player(role, hx, hy, color, is_keeper=False, is_user=False):
    my_team.append({
        'role': role,
        'home_x': hx, 'home_y': hy,
        'x': hx, 'y': hy,
        'angle': 0.0,
        'color': color,
        'is_keeper': is_keeper,
        'is_user': is_user,
        'has_ball': False,
        'prev_has_ball': False,
        'force_return_frames': 0,
        'move_range': _role_move_range('Keeper' if is_keeper else role),
        'speed': 1.0,
        'detect': ENEMY_BASE_DETECT
    })

def init_teams():
    enemies[:] = []
    my_team[:] = []

    # Opponents (red)
    add_enemy('GK', 0.0, GRID_LENGTH - 60.0, (0.86, 0.12, 0.12), 1.2, 0.9)
    add_enemy('DEF', -GOAL_MOUTH*0.35, GRID_LENGTH*0.6, (0.86, 0.12, 0.12), 1.0, 0.95)
    add_enemy('DEF',  GOAL_MOUTH*0.35, GRID_LENGTH*0.6, (0.86, 0.12, 0.12), 1.0, 0.95)
    add_enemy('MID', -GRID_LENGTH*0.15, GRID_LENGTH*0.15, (0.86, 0.12, 0.12), 1.05, 1.0)
    add_enemy('MID',  GRID_LENGTH*0.15, GRID_LENGTH*0.15, (0.86, 0.12, 0.12), 1.05, 1.0)
    add_enemy('CF', 0.0, GRID_LENGTH*0.4, (0.86, 0.12, 0.12), 1.2, 1.1)

    # Your team (blue)
    add_my_player('Keeper', 0.0, -GRID_LENGTH + 60.0, (0.0, 0.4, 1.0), is_keeper=True, is_user=False)
    add_my_player('DEF', -GOAL_MOUTH*0.35, -GRID_LENGTH*0.6, (0.0, 0.4, 1.0))
    add_my_player('DEF',  GOAL_MOUTH*0.35, -GRID_LENGTH*0.6, (0.0, 0.4, 1.0))
    add_my_player('MID', -GRID_LENGTH*0.2, -GRID_LENGTH*0.2, (0.0, 0.4, 1.0))
    add_my_player('MID',  GRID_LENGTH*0.2, -GRID_LENGTH*0.2, (0.0, 0.4, 1.0))
    add_my_player('User', 0.0, -GRID_LENGTH*0.35, (0.0, 0.6, 1.0), is_user=True)

    usr = next(p for p in my_team if p['is_user'])
    globals()['player_x'], globals()['player_y'], globals()['player_angle'] = usr['x'], usr['y'], usr['angle']

# --------------------------
# Drawing: simple humanoids (extended with limb angles for celebration)
# --------------------------
def draw_humanoid(x, y, angle_deg, torso_color=(0,1,0), limb_angles=None):
    if limb_angles is None:
        limb_angles = {'left_arm': 0, 'right_arm': 0, 'left_leg': 0, 'right_leg': 0}

    glPushMatrix()
    glTranslatef(x, y, 0)
    glRotatef(angle_deg, 0,0,1)

    # Legs
    glColor3f(0,0,0.2)
    glPushMatrix()
    glTranslatef(-BODY_WIDTH/4,0,0)
    glRotatef(limb_angles['left_leg'], 1,0,0)
    gluCylinder(gluNewQuadric(), LIMB_RADIUS*0.5, LIMB_RADIUS, LEG_LENGTH, 12, 6)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(BODY_WIDTH/4,0,0)
    glRotatef(limb_angles['right_leg'], 1,0,0)
    gluCylinder(gluNewQuadric(), LIMB_RADIUS*0.5, LIMB_RADIUS, LEG_LENGTH, 12, 6)
    glPopMatrix()

    # Torso
    glColor3f(*torso_color)
    glPushMatrix()
    glTranslatef(0,0,LEG_LENGTH + BODY_HEIGHT/2)
    glScalef(1, BODY_HEIGHT/50.0, 0.8)
    glutSolidCube(BODY_WIDTH)
    glPopMatrix()

    # Arms
    glColor3f(0.7,0.2,0.2)
    shoulder_z = LEG_LENGTH + BODY_HEIGHT * 0.9

    glPushMatrix()
    glTranslatef(-BODY_WIDTH/2,0,shoulder_z)
    glRotatef(-90 + limb_angles['left_arm'], 1,0,0)
    gluCylinder(gluNewQuadric(), LIMB_RADIUS, LIMB_RADIUS * 0.5, ARM_LENGTH, 12, 6)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(BODY_WIDTH/2,0,shoulder_z)
    glRotatef(-90 + limb_angles['right_arm'], 1,0,0)
    gluCylinder(gluNewQuadric(), LIMB_RADIUS, LIMB_RADIUS * 0.5, ARM_LENGTH, 12, 6)
    glPopMatrix()

    # Head
    glColor3f(0.0, 0.0, 0.0)
    glPushMatrix()
    head_z = LEG_LENGTH + BODY_HEIGHT + HEAD_RADIUS
    glTranslatef(0,0,head_z)
    gluSphere(gluNewQuadric(), HEAD_RADIUS * 0.85, 12, 12)
    glPopMatrix()

    glPopMatrix()

def draw_field():
    # Slight day/night tint (very subtle so default look is preserved)
    grass_c1 = getcolorformode((0.14, 0.5, 0.14), (0.10, 0.35, 0.10))
    grass_c2 = getcolorformode((0.10, 0.42, 0.10), (0.08, 0.28, 0.08))

    glPushMatrix()
    glTranslatef(-GRID_LENGTH, -GRID_LENGTH, 0)
    rows = (GRID_LENGTH * 2) // 50
    cols = (GRID_LENGTH * 2) // 50
    for i in range(int(rows)):
        for j in range(int(cols)):
            glColor3f(*grass_c1) if (i + j) % 2 == 0 else glColor3f(*grass_c2)
            x = j * 50; y = i * 50
            glBegin(GL_QUADS)
            glVertex3f(x, y, 0); glVertex3f(x+50, y, 0); glVertex3f(x+50, y+50, 0); glVertex3f(x, y+50, 0)
            glEnd()
    glPopMatrix()
    line_c = getcolorformode((1,1,1), (0.85,0.85,0.85))
    glColor3f(*line_c); glLineWidth(3)
    glBegin(GL_LINE_LOOP)
    glVertex3f(-GRID_LENGTH, -GRID_LENGTH, 0.1); glVertex3f(GRID_LENGTH, -GRID_LENGTH, 0.1)
    glVertex3f(GRID_LENGTH,  GRID_LENGTH, 0.1);  glVertex3f(-GRID_LENGTH,  GRID_LENGTH, 0.1)
    glEnd()
    glBegin(GL_LINES)
    glVertex3f(-GRID_LENGTH, 0, 0.1); glVertex3f(GRID_LENGTH, 0, 0.1); glEnd()
    glBegin(GL_LINE_LOOP)
    R = GRID_LENGTH * 0.22
    for k in range(80):
        a = 2*math.pi*k/80
        glVertex3f(R*math.cos(a), R*math.sin(a), 0.1)
    glEnd()
    glBegin(GL_LINES)
    glVertex3f(-GOAL_MOUTH/2,  GRID_LENGTH, 0.1); glVertex3f( GOAL_MOUTH/2,  GRID_LENGTH, 0.1)
    glVertex3f(-GOAL_MOUTH/2, -GRID_LENGTH, 0.1); glVertex3f( GOAL_MOUTH/2, -GRID_LENGTH, 0.1)
    glEnd()

def draw_goals():
    glColor3f(1,1,1); glLineWidth(6)
    post_h = 80.0; net_depth = 100.0; net_rows = 12; net_cols = 16
    for y_front, y_back in [(GRID_LENGTH, GRID_LENGTH - net_depth),
                            (-GRID_LENGTH, -GRID_LENGTH + net_depth)]:
        glBegin(GL_LINES)
        glVertex3f(-GOAL_MOUTH/2, y_front, 0); glVertex3f(-GOAL_MOUTH/2, y_front, post_h)
        glVertex3f( GOAL_MOUTH/2, y_front, 0); glVertex3f( GOAL_MOUTH/2, y_front, post_h)
        glVertex3f(-GOAL_MOUTH/2, y_front, post_h); glVertex3f( GOAL_MOUTH/2, y_front, post_h)
        glEnd()
        glBegin(GL_LINES)
        glVertex3f(-GOAL_MOUTH/2, y_front, 0); glVertex3f(-GOAL_MOUTH/2, y_back, 0)
        glVertex3f(-GOAL_MOUTH/2, y_front, post_h); glVertex3f(-GOAL_MOUTH/2, y_back, post_h)
        glVertex3f( GOAL_MOUTH/2, y_front, 0); glVertex3f( GOAL_MOUTH/2, y_back, 0)
        glVertex3f( GOAL_MOUTH/2, y_front, post_h); glVertex3f( GOAL_MOUTH/2, y_back, post_h)
        glEnd()
        glColor3f(0.9,0.9,0.9); glLineWidth(2)
        for j in range(net_cols+1):
            x = -GOAL_MOUTH/2 + (j/net_cols) * GOAL_MOUTH
            glBegin(GL_LINES); glVertex3f(x, y_front, post_h); glVertex3f(x, y_back, post_h); glEnd()
        for k in range(6):
            y = y_front + (k/5.0) * (y_back - y_front)
            glBegin(GL_LINES); glVertex3f(-GOAL_MOUTH/2, y, post_h); glVertex3f(GOAL_MOUTH/2, y, post_h); glEnd()
        for i in range(net_rows+1):
            z = (i/net_rows) * post_h
            glBegin(GL_LINES); glVertex3f(-GOAL_MOUTH/2, y_front, z); glVertex3f(-GOAL_MOUTH/2, y_back, z); glEnd()
            glBegin(GL_LINES); glVertex3f( GOAL_MOUTH/2, y_front, z); glVertex3f( GOAL_MOUTH/2, y_back, z); glEnd()

def draw_ball():
    glPushMatrix()
    glColor3f(*getcolorformode((1,1,1), (0.85,0.85,0.9)))
    glTranslatef(ball['x'], ball['y'], ball['z'])
    glutSolidSphere(BALL_RADIUS, 20, 20)
    glPopMatrix()

def draw_all_players():
    for p in my_team:
        la = animationlimbingles if (p.get('is_user', False) and iscelebrating) else None
        draw_humanoid(p['x'], p['y'], p['angle'], torso_color=p['color'], limb_angles=la)
    for e in enemies:
        draw_humanoid(e['x'], e['y'], e['angle'], torso_color=e['color'])

# --------------------------
# Possession + contact logic
# --------------------------
def _contact_reach(): return (BODY_WIDTH*0.9) + BALL_RADIUS + 6.0

def update_possession():
    # remember previous flags
    for p in my_team:
        p['prev_has_ball'] = p['has_ball']; p['has_ball'] = False
    for e in enemies:
        e['prev_has_ball'] = e['has_ball']; e['has_ball'] = False

    holder_id = GG3D_Possession('holder')

    if holder_id is not None:
        hp = next((pp for pp in my_team + enemies if id(pp) == holder_id), None)
        if hp is not None:
            hp['has_ball'] = True
        for g in (my_team, enemies):
            for p in g:
                if p['prev_has_ball'] and id(p) != holder_id:
                    p['force_return_frames'] = 90
        return

    # Otherwise, allow nearest-in-contact to claim (and start the lock)
    best = None; bestd = 1e9
    def consider(px, py, who):
        d = dist2d(px, py, ball['x'], ball['y'])
        if d <= _contact_reach():
            nonlocal best, bestd
            if d < bestd: best, bestd = who, d

    for p in my_team: consider(p['x'], p['y'], p)
    for e in enemies: consider(e['x'], e['y'], e)
    if best is not None and GG3D_Possession('can_take', player=best):
        GG3D_Possession('set', player=best, duration_ms=3000)
        best['has_ball'] = True
        # switch control if it's our teammate
        if best in my_team:
            transfer_control_to(best)

# --------------------------
# Physics, interception & AI
# --------------------------
def intercept_capture(prevx, prevy):
    """If the ball's path crossed near any player's coordinate, capture it."""
    if GG3D_Penalty('active'):  # skip during penalties
        return
    CAPTURE_R = BODY_WIDTH * 0.75 + BALL_RADIUS + 4.0

    best = None
    best_t = 2.0  # segment param; lower = earlier along path

    # check all players on both teams
    for p in my_team + enemies:
        d, t, _, _ = dist_point_to_segment(p['x'], p['y'], prevx, prevy, ball['x'], ball['y'])
        if d <= CAPTURE_R and t < best_t and GG3D_Possession('can_take', player=p):
            best = p; best_t = t

    if best is not None:
        GG3D_Possession('set', player=best, duration_ms=3000)
        best['has_ball'] = True
        # soften the shot/pass so the ball stays controllable
        ball['vx'] *= 0.45; ball['vy'] *= 0.45; ball['vz'] *= 0.45
        # if it's our team, hand over control
        if best in my_team:
            transfer_control_to(best)

def update_ball():
    global player_score, ai_score, iscelebrating, isinreplay, replaytimer, replaycameraangle
    # If celebrating or in replay, freeze ball physics to keep the scene steady
    if iscelebrating or isinreplay:
        return

    # store previous position for interception checks
    prevx, prevy = ball['x'], ball['y']

    # advance
    ball['x'] += ball['vx']; ball['y'] += ball['vy']
    ball['vx'] *= BALL_FRICTION; ball['vy'] *= BALL_FRICTION
    if abs(ball['vx']) < 0.01: ball['vx'] = 0.0
    if abs(ball['vy']) < 0.01: ball['vy'] = 0.0

    # interception BEFORE goal/side checks (so players can cut passes)
    intercept_capture(prevx, prevy)

    # side walls
    if ball['x'] < -GRID_LENGTH:
        ball['x'] = -GRID_LENGTH; ball['vx'] = -ball['vx'] * 0.7
    elif ball['x'] > GRID_LENGTH:
        ball['x'] = GRID_LENGTH;  ball['vx'] = -ball['vx'] * 0.7

    # goals/out
    if ball['y'] > GRID_LENGTH:
        if abs(ball['x']) <= GOAL_MOUTH/2:
            player_score += 1
            # Trigger celebration + start replay
            iscelebrating = celebration('start')
            isinreplay = True
            replaytimer = 300
            replaycameraangle = 1
            reset_ball()
        else:
            ball['y'] = GRID_LENGTH; ball['vy'] = -ball['vy'] * 0.7
    elif ball['y'] < -GRID_LENGTH:
        if abs(ball['x']) <= GOAL_MOUTH/2:
            ai_score += 1; reset_ball()
        else:
            ball['y'] = -GRID_LENGTH; ball['vy'] = -ball['vy'] * 0.7

    # height
    ball['z'] += ball['vz']; ball['vz'] += GRAVITY_Z
    if ball['z'] > BALL_RADIUS + 0.01:
        ball['vx'] *= AIR_DRAG; ball['vy'] *= AIR_DRAG
    if ball['z'] < BALL_RADIUS:
        ball['z'] = BALL_RADIUS
        if ball['vz'] < 0.0:
            ball['vz'] = -ball['vz'] * BOUNCE_Z
            if abs(ball['vz']) < 0.15: ball['vz'] = 0.0

    # drop lock if ball far from holder (safety)
    holder_id = GG3D_Possession('holder')
    if holder_id is not None:
        hp = next((pp for pp in my_team + enemies if id(pp) == holder_id), None)
        if hp is not None and dist2d(ball['x'], ball['y'], hp['x'], hp['y']) > 140.0:
            GG3D_Possession('clear')

def _step_toward(p, tx, ty, speed):
    ux, uy = unit_vec(tx - p['x'], ty - p['y'])
    p['x'] += ux * speed; p['y'] += uy * speed
    p['x'] = clamp(p['x'], -GRID_LENGTH, GRID_LENGTH)
    p['y'] = clamp(p['y'], -GRID_LENGTH, GRID_LENGTH)

def _ret_home(p, rate=0.5):
    _step_toward(p, p['home_x'], p['home_y'], rate)

# --- Advanced GK movement (patrol + track, saves, kicks) ---
def update_goalkeeper_xy(p, ball):
    goal_top    =  GRID_LENGTH - 60.0
    goal_bottom = -GRID_LENGTH + 60.0
    mouth_half  = GOAL_MOUTH * 0.5
    slide_limit = GOAL_MOUTH * 0.48
    home_y = p.get('home_y', p.get('y', 0.0))
    is_top_goal = abs(home_y - goal_top) < abs(home_y - goal_bottom)
    goal_y = goal_top if is_top_goal else goal_bottom

    GK_SAVE_ZONE_Y = 140.0
    PATROL_AMPL     = slide_limit * 0.75
    PATROL_SPEED    = 0.055
    EASE_X          = 0.18
    MAX_STEP_X      = 0.85
    SPACE_KICK_SPEED = 1.2

    if is_top_goal:
        inbound = (ball['vy'] > 0.0) and (ball['y'] >= goal_top - GK_SAVE_ZONE_Y)
        dist_y  = max(1.0, goal_top - ball['y'])
    else:
        inbound = (ball['vy'] < 0.0) and (ball['y'] <= goal_bottom + GK_SAVE_ZONE_Y)
        dist_y  = max(1.0, ball['y'] - goal_bottom)

    phase = p.get('gk_phase', 0.0) + PATROL_SPEED
    if phase > (math.pi * 2.0): phase -= (math.pi * 2.0)
    p['gk_phase'] = phase
    patrol_x = math.sin(phase) * (slide_limit * 0.75)

    in_mouth = abs(ball['x']) <= mouth_half
    if inbound and in_mouth:
        ball_speed = math.hypot(ball['vx'], ball['vy'])
        w = 1.0 - (dist_y / GK_SAVE_ZONE_Y)
        w = max(0.35, min(0.95, w + 0.15 * (ball_speed / 20.0)))
        track_x = clamp(ball['x'], -slide_limit, slide_limit)
        target_x = (1.0 - w) * patrol_x + w * track_x
    else:
        target_x = patrol_x

    step_x = (target_x - p['x']) * EASE_X
    if abs(step_x) > MAX_STEP_X:
        step_x = MAX_STEP_X if step_x > 0.0 else -MAX_STEP_X

    p['x'] = clamp(p['x'] + step_x, -slide_limit, slide_limit)
    p['y'] = goal_y

    dx = ball['x'] - p['x']; dy = ball['y'] - p['y']
    if dx*dx + dy*dy > 1e-6:
        p['angle'] = math.degrees(math.atan2(dy, dx)) - 90.0

    # simple save/clear
    if abs(ball['x'] - p['x']) < BODY_WIDTH * 0.9 and abs(ball['y'] - p['y']) < BODY_HEIGHT * 0.5:
        kick_direction_x = math.cos(math.radians(p['angle'] + 90))
        kick_direction_y = math.sin(math.radians(p['angle'] + 90))
        if math.hypot(ball['vx'], ball['vy']) < 5.0:
            ball['vx'] = kick_direction_x * SPACE_KICK_SPEED
            ball['vy'] = kick_direction_y * SPACE_KICK_SPEED
        else:
            ball['vx'] = kick_direction_x * ENEMY_KICK
            ball['vy'] = kick_direction_y * ENEMY_KICK
        ball['vz'] *= 0.5
        ball['x'] = p['x']; ball['y'] = p['y']

def _team_choose_single_chaser(team, exclude_keeper=True, exclude_user=False):
    best = None; best_d = 1e9
    for p in team:
        if exclude_keeper and p.get('is_keeper', False): continue
        if exclude_user   and p.get('is_user',   False): continue
        if dist2d(p['home_x'], p['home_y'], ball['x'], ball['y']) > p.get('move_range', 1e9):
            continue
        dx = ball['x'] - p['x']; dy = ball['y'] - p['y']
        d = math.hypot(dx, dy)
        if d <= p.get('detect', 1e9) and d < best_d:
            best, best_d = p, d
    return best

def enemy_ai_update():
    chaser = _team_choose_single_chaser(enemies, exclude_keeper=True, exclude_user=False)
    for e in enemies:
        dx = ball['x'] - e['x']; dy = ball['y'] - e['y']; d = math.hypot(dx, dy)
        if d > 1e-6: e['angle'] = math.degrees(math.atan2(dy, dx)) - 90

        if e.get('is_keeper', False):
            update_goalkeeper_xy(e, ball); continue

        if e['force_return_frames'] > 0:
            e['force_return_frames'] -= 1; _ret_home(e, rate=e['speed'] * 0.6); continue

        if e is chaser:
            _step_toward(e, ball['x'], ball['y'], e['speed'])
            if d <= _contact_reach() and GG3D_Possession('can_take', player=e):
                GG3D_Possession('set', player=e, duration_ms=3000)
                e['has_ball'] = True
            if e['has_ball'] and GG3D_Possession('holder') == id(e):
                ux, uy = unit_vec(0.0 - ball['x'], (-GRID_LENGTH - 50.0) - ball['y'])
                ball['vx'] += ux * (e['speed'] * 0.8); ball['vy'] += uy * (e['speed'] * 0.8)
                cap_ball_speed()
        else:
            _ret_home(e, rate=e['speed'] * 0.6)

def my_team_update():
    chaser = _team_choose_single_chaser(my_team, exclude_keeper=True, exclude_user=True)
    for p in my_team:
        if p.get('is_user', False):  # user handled by keyboard
            continue

        dx = ball['x'] - p['x']; dy = ball['y'] - p['y']; d = math.hypot(dx, dy)
        if d > 1e-6: p['angle'] = math.degrees(math.atan2(dy, dx)) - 90

        if p.get('is_keeper', False):
            update_goalkeeper_xy(p, ball); continue

        if p['force_return_frames'] > 0:
            p['force_return_frames'] -= 1; _ret_home(p, rate=0.6); continue

        if p is chaser:
            _step_toward(p, ball['x'], ball['y'], p.get('speed', 1.0))
            if d <= _contact_reach() and GG3D_Possession('can_take', player=p):
                GG3D_Possession('set', player=p, duration_ms=3000)
                p['has_ball'] = True
        else:
            _ret_home(p, rate=0.5)

# --------------------------
# Player control & actions (kick, dribble, long shot)
# --------------------------


# ---- Kicks & Long Shots (REPLACE your versions) ----------
def try_kick(strong=True):
    holder = GG3D_Possession('holder')
    user = _user_player()
    if user is None:
        return False

    # If someone else has the 3s lock, you can't kick
    if holder is not None and holder != id(user):
        return False

    if not _kick_contact_ok_for_user():
        return False

    # Direction: use current facing
    rad = math.radians(player_angle + 90)
    dirx, diry = math.cos(rad), math.sin(rad)

    # Power
    pwr = KICK_POWER if strong else (KICK_POWER * 0.55)

    # Apply
    ball['vx'] += dirx * pwr
    ball['vy'] += diry * pwr
    cap_ball_speed()  # full cap for normal kick

    # Kick releases possession
    GG3D_Possession('clear')
    return True


def try_long_shot():
    holder = GG3D_Possession('holder')
    user = _user_player()
    if user is None:
        return False

    # If someone else has the 3s lock, you can't kick
    if holder is not None and holder != id(user):
        return False

    if not _kick_contact_ok_for_user():
        return False

    # Direction: use current facing
    rad = math.radians(player_angle + 90)
    dirx, diry = math.cos(rad), math.sin(rad)

    # Big pace + lift
    ball['vx'] += dirx * (KICK_POWER * 1.9)
    ball['vy'] += diry * (KICK_POWER * 1.9)
    ball['vz'] += LONG_SHOT_LIFT
    cap_ball_speed()  # keep horizontal speed within global cap

    GG3D_Possession('clear')
    return True

# ---- Helpers (new, tiny) ---------------------------------
def _user_player():
    return next((pp for pp in my_team if pp.get('is_user', False)), None)

def _kick_contact_ok_for_user():
    """More forgiving contact: either near the foot *or* near player center."""
    # forward foot point
    rad = math.radians(player_angle + 90)
    foot_x = player_x + math.cos(rad) * (BODY_WIDTH * 0.9 + 6.0)
    foot_y = player_y + math.sin(rad) * (BODY_WIDTH * 0.9 + 6.0)

    d_foot   = dist2d(foot_x,  foot_y,  ball['x'], ball['y'])
    d_center = dist2d(player_x, player_y, ball['x'], ball['y'])

    # original reach + a center fallback
    foot_reach   = KICK_REACH + BALL_RADIUS
    center_reach = (BODY_WIDTH * 1.5) + BALL_RADIUS + 10.0

    return (d_foot <= foot_reach) or (d_center <= center_reach)

# ---- Dribble Nudge (REPLACE your version) ----------------
def maybe_dribble_push(is_moving_forward):
    """
    Gentle nudge only when moving forward, only by the holder (you),
    keeps a minimal gap so you can always shoot/pass cleanly.
    """
    if not is_moving_forward:
        return
    user = _user_player()
    if user is None:
        return
    holder = GG3D_Possession('holder')
    if holder is not None and holder != id(user):
        return  # only the holder may influence the ball

    # If ball already has decent pace, don't add more
    if math.hypot(ball['vx'], ball['vy']) > DRIBBLE_MAX_SPEED:
        return

    rad = math.radians(player_angle + 90)
    ahead_x = player_x + math.cos(rad) * (BODY_WIDTH * 1.1 + 6.0)
    ahead_y = player_y + math.sin(rad) * (BODY_WIDTH * 1.1 + 6.0)
    gap = dist2d(ahead_x, ahead_y, ball['x'], ball['y'])

    # Keep a small gap; if it's too close, do NOT push (so kicks aren't blocked)
    if gap <= DRIBBLE_MIN_GAP:
        return

    # Small proportional nudge
    push = min(DRIBBLE_PUSH * 0.45, max(0.08, (gap - DRIBBLE_MIN_GAP) * 0.06))
    ball['vx'] += math.cos(rad) * push
    ball['vy'] += math.sin(rad) * push
    cap_ball_speed(DRIBBLE_MAX_SPEED)  # soft cap while dribbling

    # Refresh short possession window to you
    GG3D_Possession('set', player=user, duration_ms=3000)

# --------------------------
# HUD drawing
# --------------------------
def GG3D_DrawLongShotBanner(draw_text, x=10, y=120):
    now = glutGet(GLUT_ELAPSED_TIME)
    if now < globals().get('long_shot_msg_until', -1):
        draw_text(x, y, "🔥 LONG SHOT!")

def draw_hud():
    now = glutGet(GLUT_ELAPSED_TIME)
    remaining = match_ms - (now - match_start_ms)
    draw_text(10, WINDOW_HEIGHT-28, f"Time: {max(0, remaining//1000)}s")
    draw_text(10, WINDOW_HEIGHT-52, f"Score You {player_score} : {ai_score} AI")
    draw_text(10, WINDOW_HEIGHT-76, "Kick: SPACE | Long Shot: L | Move: WASD | RightClick: FPP | T: TopDown | R: Restart | C: Switch | P: Penalty | N: Day/Night | M: Rain")
    GG3D_SprintEnergy('draw', draw_text=draw_text, x=10, y=WINDOW_HEIGHT-100)
    GG3D_DrawLongShotBanner(draw_text, x=10, y=120)
    holder_id = GG3D_Possession('holder')
    draw_text(10, WINDOW_HEIGHT-124, "Holder: " + ("None" if holder_id is None else "Locked"))
    GG3D_Penalty('draw_hud', draw_text=draw_text, x=10, y=80)
    if isinreplay:
        draw_text(WINDOW_WIDTH//2 - 120, 40, "REPLAY MODE - Press 1, 2, 3")

    if game_over:
        winner = "You Win!" if player_score > ai_score else ("Draw!" if player_score == ai_score else "AI Wins!")
        draw_text(WINDOW_WIDTH//2 - 60, WINDOW_HEIGHT//2 + 20, "GAME OVER")
        draw_text(WINDOW_WIDTH//2 - 60, WINDOW_HEIGHT//2 - 4, winner)
        draw_text(WINDOW_WIDTH//2 - 120, WINDOW_HEIGHT//2 - 28, "Press R to Restart")

# --------------------------
# Camera setup & display
# --------------------------
def setupCamera():
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(fovY, WINDOW_WIDTH / WINDOW_HEIGHT, 0.1, 4000)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()
    if isinreplay:
        setreplaycamera(); return
    if topdown_view:
        gluLookAt(0, 0, 1400, 0,0,0, 0,1,0); return
    if first_person:
        cam_x = player_x; cam_y = player_y; cam_z = LEG_LENGTH + BODY_HEIGHT + HEAD_RADIUS*2
        rad = math.radians(player_angle + 90)
        look_x = player_x + math.cos(rad) * 120
        look_y = player_y + math.sin(rad) * 120
        gluLookAt(cam_x, cam_y, cam_z, look_x, look_y, cam_z, 0,0,1)
    else:
        cam_x = camera_radius * math.cos(math.radians(camera_angle))
        cam_y = camera_radius * math.sin(math.radians(camera_angle))
        cam_z = camera_height
        gluLookAt(cam_x, cam_y, cam_z, 0,0,0, 0,0,1)

def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()
    glViewport(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
    setupCamera()

    draw_field()
    draw_goals()
    weather('draw')      # AFSANA: rain draw
    draw_ball()
    draw_all_players()
    draw_hud()

    glutSwapBuffers()
    glutPostRedisplay()

# --------------------------
# Input handling
# --------------------------
def specialKeyListener(key, x, y):
    global camera_angle, camera_height
    if not first_person and not topdown_view and not isinreplay:
        if key == GLUT_KEY_UP: camera_height += 30
        elif key == GLUT_KEY_DOWN: camera_height -= 30
        elif key == GLUT_KEY_LEFT: camera_angle += 5
        elif key == GLUT_KEY_RIGHT: camera_angle -= 5
    glutPostRedisplay()

def _switch_control_to_nearest_teammate():
    global player_x, player_y, player_angle
    current = next((p for p in my_team if p.get('is_user', False)), None)
    if current is None:
        return
    best = None; bestd = 1e9
    for p in my_team:
        if p is current: continue
        if p.get('is_keeper', False): continue
        d = dist2d(current['x'], current['y'], p['x'], p['y'])
        if d < bestd:
            best, bestd = p, d
    if best is None: return
    transfer_control_to(best)

def keyboardListener(key, x, y):
    global player_x, player_y, player_angle, game_over, player_score, ai_score
    global match_start_ms, first_person, topdown_view, long_shot_msg_until
    global replaycameraangle, isinreplay

    try: raw = key.decode("utf-8")
    except: return
    k = raw.lower()

    if k == '\x1b':
        try: glutLeaveMainLoop()
        except: pass
        return

    # Replay camera controls take precedence
    if isinreplay:
        if k == '1': replaycameraangle = 1
        elif k == '2': replaycameraangle = 2
        elif k == '3': replaycameraangle = 3
        return

    # Day/Night + Rain toggles
    if k == 'n': weather('toggle_day_night'); return
    if k == 'm': weather('toggle_rain'); return

    if GG3D_Penalty('active'):
        if k == ' ':
            GG3D_Penalty('shoot', ball=ball)
        return

    if k == 'r' and game_over:
        player_score = 0; ai_score = 0
        reset_ball(); init_teams()
        spawn_ball_at_user_feet()
        game_over = False
        match_start_ms = glutGet(GLUT_ELAPSED_TIME)
        return

    if game_over: return

    if k == 't': topdown_view = not topdown_view
    elif k == 'c': _switch_control_to_nearest_teammate(); return
    elif k == 'p':
        shooter = next((pp for pp in my_team if pp.get('is_user', False)), None)
        keeper  = next((ee for ee in enemies if ee.get('is_keeper', False)), None)
        if shooter and keeper:
            GG3D_Penalty('start', ball=ball, shooter=shooter, keeper=keeper)
        return
    elif k == 'l':
        if try_long_shot():
            long_shot_msg_until = glutGet(GLUT_ELAPSED_TIME) + LONG_SHOT_MSG_MS

    move_step  = 10 * PLAYER_SCALE
    angle_step = 6
    _sprint_now = raw.isalpha() and raw.isupper()
    mult = GG3D_SprintEnergy('maybe_scale', want_sprint=_sprint_now)

    if k == 'w':
        rad = math.radians(player_angle + 90)
        player_x += math.cos(rad) * move_step * mult
        player_y += math.sin(rad) * move_step * mult
        maybe_dribble_push(True)
    elif k == 's':
        rad = math.radians(player_angle + 90)
        player_x -= math.cos(rad) * move_step * mult
        player_y -= math.sin(rad) * move_step * mult
    elif k == 'a':
        player_angle += angle_step
    elif k == 'd':
        player_angle -= angle_step
    elif k == ' ':
        try_kick(True)

    player_x = clamp(player_x, -GRID_LENGTH, GRID_LENGTH)
    player_y = clamp(player_y, -GRID_LENGTH, GRID_LENGTH)

    user = next((p for p in my_team if p.get('is_user', False)), None)
    if user:
        user['x'], user['y'], user['angle'] = player_x, player_y, player_angle

    glutPostRedisplay()

def mouseListener(button, state, x, y):
    global first_person
    if button == GLUT_RIGHT_BUTTON and state == GLUT_DOWN and not isinreplay:
        first_person = not first_person
    if button == GLUT_LEFT_BUTTON and state == GLUT_DOWN and not game_over and not GG3D_Penalty('active'):
        try_kick(True)
    glutPostRedisplay()

# --------------------------
# Idle loop
# --------------------------
def idle_update():
    global game_over, iscelebrating, animationlimbingles, isinreplay, replaytimer
    GG3D_SprintEnergy('tick')

    # Weather tick regardless
    weather('update')

    # Celebration & Replay handling
    if iscelebrating:
        iscelebrating, animationlimbingles = celebration('update', animationlimbingles)

    if isinreplay:
        replaytimer -= 1
        if replaytimer <= 0:
            isinreplay = False

    if GG3D_Penalty('active'):
        GG3D_Penalty('update', ball=ball, my_team=my_team, enemies=enemies)
        update_ball()
    elif not game_over and not isinreplay:
        update_possession()
        enemy_ai_update()
        my_team_update()
        update_ball()

        user = next((p for p in my_team if p.get('is_user', False)), None)
        if user:
            user['x'] = player_x; user['y'] = player_y; user['angle'] = player_angle

        now = glutGet(GLUT_ELAPSED_TIME)
        remaining = match_ms - (now - match_start_ms)
        if remaining <= 0:
            game_over = True

    glutPostRedisplay()
    glutTimerFunc(16, lambda t=0: idle_update(), 0)

# --------------------------
# OpenGL init & main
# --------------------------
def init_gl():
    glClearColor(0.18, 0.3, 0.55, 1.0)
    glEnable(GL_DEPTH_TEST)
    glShadeModel(GL_SMOOTH)
    glViewport(0, 0, WINDOW_WIDTH, WINDOW_HEIGHT)
    # AFSANA: helpful GL enables for nicer rain/lines and alpha
    glEnable(GL_BLEND)
    glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
    glEnable(GL_LINE_SMOOTH)
    glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

def main():
    global match_start_ms
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutInitWindowPosition(100, 60)
    glutCreateWindow(b"GoalGlide 3D - Intercepts, Possession, GK, Penalty, Long Shot + Replay/Weather/Celebration")

    init_gl()
    init_teams()
    reset_ball()
    spawn_ball_at_user_feet()
    initweather()   # AFSANA: init rain particles
    match_start_ms = glutGet(GLUT_ELAPSED_TIME)

    glutDisplayFunc(display)
    glutKeyboardFunc(keyboardListener)
    glutSpecialFunc(specialKeyListener)
    glutMouseFunc(mouseListener)

    glutTimerFunc(16, lambda t=0: idle_update(), 0)
    glutMainLoop()

if __name__ == "__main__":
    main()
