
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math

# =======================
# WINDOW SETTINGS
# =======================
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800

# =======================
# FIELD SETTINGS
# =======================
FIELD_LENGTH = 800
FIELD_WIDTH = 500
CENTER_CIRCLE_RADIUS = 60
GOAL_WIDTH = 200
GOAL_DEPTH = 60

# =======================
# PLAYER SETTINGS
# =======================
player_x, player_y = 0, 0
player_angle = 0
PLAYER_SPEED = 10

# Humanoid proportions
BODY_WIDTH = 40
BODY_HEIGHT = 80
HEAD_RADIUS = 20
ARM_LENGTH = 40
LEG_LENGTH = 50

# =======================
# BALL SETTINGS
# =======================
ball_x, ball_y = 50, 0
BALL_RADIUS = 15

# =======================
# FIELD DRAWING FUNCTIONS
# =======================
def draw_field():
    """Draws the football field with center circle, lines, and goals"""
    glColor3f(0.0, 0.5, 0.0)  # Green field
    glBegin(GL_QUADS)
    glVertex3f(-FIELD_LENGTH/2, -FIELD_WIDTH/2, 0)
    glVertex3f(FIELD_LENGTH/2, -FIELD_WIDTH/2, 0)
    glVertex3f(FIELD_LENGTH/2, FIELD_WIDTH/2, 0)
    glVertex3f(-FIELD_LENGTH/2, FIELD_WIDTH/2, 0)
    glEnd()

    # White boundary
    glColor3f(1, 1, 1)
    glBegin(GL_LINE_LOOP)
    glVertex3f(-FIELD_LENGTH/2, -FIELD_WIDTH/2, 0.01)
    glVertex3f(FIELD_LENGTH/2, -FIELD_WIDTH/2, 0.01)
    glVertex3f(FIELD_LENGTH/2, FIELD_WIDTH/2, 0.01)
    glVertex3f(-FIELD_LENGTH/2, FIELD_WIDTH/2, 0.01)
    glEnd()

    # Center line
    glBegin(GL_LINES)
    glVertex3f(0, -FIELD_WIDTH/2, 0.01)
    glVertex3f(0, FIELD_WIDTH/2, 0.01)
    glEnd()

    # Center circle
    glPushMatrix()
    glTranslatef(0, 0, 0.01)
    draw_circle(CENTER_CIRCLE_RADIUS)
    glPopMatrix()

    # Goals
    draw_goal_area(-FIELD_LENGTH/2)
    draw_goal_area(FIELD_LENGTH/2)

def draw_circle(radius, segments=100):
    """Helper: draws a circle"""
    glBegin(GL_LINE_LOOP)
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        glVertex3f(x, y, 0)
    glEnd()

def draw_goal_area(xpos):
    """Draws goal area rectangle"""
    glBegin(GL_LINE_LOOP)
    glVertex3f(xpos, -GOAL_WIDTH/2, 0.01)
    glVertex3f(xpos, GOAL_WIDTH/2, 0.01)
    glVertex3f(xpos + math.copysign(GOAL_DEPTH, xpos), GOAL_WIDTH/2, 0.01)
    glVertex3f(xpos + math.copysign(GOAL_DEPTH, xpos), -GOAL_WIDTH/2, 0.01)
    glEnd()

# =======================
# PLAYER (HUMANOID)
# =======================
def draw_player(x, y, angle, team_color=(0, 0, 1)):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glRotatef(angle, 0, 0, 1)

    # Body
    glColor3f(*team_color)
    glPushMatrix()
    glScalef(0.6, 0.3, 1.5)
    glutSolidCube(BODY_WIDTH)
    glPopMatrix()

    # Head
    glColor3f(1, 0.8, 0.6)
    glPushMatrix()
    glTranslatef(0, 0, BODY_HEIGHT/2 + HEAD_RADIUS)
    glutSolidSphere(HEAD_RADIUS, 20, 20)
    glPopMatrix()

    # Arms
    glColor3f(*team_color)
    glPushMatrix()
    glTranslatef(BODY_WIDTH/2, 0, BODY_HEIGHT/2 - 5)
    glScalef(0.4, 0.2, 1.0)
    glutSolidCube(ARM_LENGTH)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(-BODY_WIDTH/2, 0, BODY_HEIGHT/2 - 5)
    glScalef(0.4, 0.2, 1.0)
    glutSolidCube(ARM_LENGTH)
    glPopMatrix()

    # Legs
    glColor3f(*team_color)
    glPushMatrix()
    glTranslatef(BODY_WIDTH/4, 0, -BODY_HEIGHT/2)
    glScalef(0.3, 0.3, 1.2)
    glutSolidCube(LEG_LENGTH)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(-BODY_WIDTH/4, 0, -BODY_HEIGHT/2)
    glScalef(0.3, 0.3, 1.2)
    glutSolidCube(LEG_LENGTH)
    glPopMatrix()

    glPopMatrix()

# =======================
# BALL
# =======================
def draw_ball(x, y):
    glColor3f(1, 1, 1)  # White ball
    glPushMatrix()
    glTranslatef(x, y, BALL_RADIUS)
    glutSolidSphere(BALL_RADIUS, 20, 20)
    glPopMatrix()

# =======================
# CONTROLS
# =======================
def special_keys(key, x, y):
    global player_x, player_y, player_angle, ball_x, ball_y
    if key == GLUT_KEY_UP:
        player_y += PLAYER_SPEED
    elif key == GLUT_KEY_DOWN:
        player_y -= PLAYER_SPEED
    elif key == GLUT_KEY_LEFT:
        player_x -= PLAYER_SPEED
        player_angle = 90
    elif key == GLUT_KEY_RIGHT:
        player_x += PLAYER_SPEED
        player_angle = -90

    # Ball interaction (kick if close)
    dx, dy = ball_x - player_x, ball_y - player_y
    dist = math.sqrt(dx*dx + dy*dy)
    if dist < 50:
        ball_x += dx * 0.5
        ball_y += dy * 0.5

    glutPostRedisplay()

# =======================
# DISPLAY
# =======================
def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # Camera setup
    gluLookAt(0, -1000, 600, 0, 0, 0, 0, 0, 1)

    # Draw objects
    draw_field()
    draw_player(player_x, player_y, player_angle)
    draw_ball(ball_x, ball_y)

    glutSwapBuffers()

# =======================
# MAIN
# =======================
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutCreateWindow(b"GoalGlide 3D_SdRoCk")

    glEnable(GL_DEPTH_TEST)

    glutDisplayFunc(display)
    glutSpecialFunc(special_keys)

    glClearColor(0, 0.6, 0, 1)  # Background green
    glutMainLoop()

if __name__ == "__main__":
    main()
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math

# =======================
# WINDOW SETTINGS
# =======================
WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 800

# =======================
# FIELD SETTINGS
# =======================
FIELD_LENGTH = 800
FIELD_WIDTH = 500
CENTER_CIRCLE_RADIUS = 60
GOAL_WIDTH = 200
GOAL_DEPTH = 60

# =======================
# PLAYER SETTINGS
# =======================
player_x, player_y = 0, 0
player_angle = 0
PLAYER_SPEED = 10

# Humanoid proportions
BODY_WIDTH = 40
BODY_HEIGHT = 80
HEAD_RADIUS = 20
ARM_LENGTH = 40
LEG_LENGTH = 50

# =======================
# BALL SETTINGS
# =======================
ball_x, ball_y = 50, 0
BALL_RADIUS = 15

# =======================
# FIELD DRAWING FUNCTIONS
# =======================
def draw_field():
    """Draws the football field with center circle, lines, and goals"""
    glColor3f(0.0, 0.5, 0.0)  # Green field
    glBegin(GL_QUADS)
    glVertex3f(-FIELD_LENGTH/2, -FIELD_WIDTH/2, 0)
    glVertex3f(FIELD_LENGTH/2, -FIELD_WIDTH/2, 0)
    glVertex3f(FIELD_LENGTH/2, FIELD_WIDTH/2, 0)
    glVertex3f(-FIELD_LENGTH/2, FIELD_WIDTH/2, 0)
    glEnd()

    # White boundary
    glColor3f(1, 1, 1)
    glBegin(GL_LINE_LOOP)
    glVertex3f(-FIELD_LENGTH/2, -FIELD_WIDTH/2, 0.01)
    glVertex3f(FIELD_LENGTH/2, -FIELD_WIDTH/2, 0.01)
    glVertex3f(FIELD_LENGTH/2, FIELD_WIDTH/2, 0.01)
    glVertex3f(-FIELD_LENGTH/2, FIELD_WIDTH/2, 0.01)
    glEnd()

    # Center line
    glBegin(GL_LINES)
    glVertex3f(0, -FIELD_WIDTH/2, 0.01)
    glVertex3f(0, FIELD_WIDTH/2, 0.01)
    glEnd()

    # Center circle
    glPushMatrix()
    glTranslatef(0, 0, 0.01)
    draw_circle(CENTER_CIRCLE_RADIUS)
    glPopMatrix()

    # Goals
    draw_goal_area(-FIELD_LENGTH/2)
    draw_goal_area(FIELD_LENGTH/2)

def draw_circle(radius, segments=100):
    """Helper: draws a circle"""
    glBegin(GL_LINE_LOOP)
    for i in range(segments):
        angle = 2 * math.pi * i / segments
        x = math.cos(angle) * radius
        y = math.sin(angle) * radius
        glVertex3f(x, y, 0)
    glEnd()

def draw_goal_area(xpos):
    """Draws goal area rectangle"""
    glBegin(GL_LINE_LOOP)
    glVertex3f(xpos, -GOAL_WIDTH/2, 0.01)
    glVertex3f(xpos, GOAL_WIDTH/2, 0.01)
    glVertex3f(xpos + math.copysign(GOAL_DEPTH, xpos), GOAL_WIDTH/2, 0.01)
    glVertex3f(xpos + math.copysign(GOAL_DEPTH, xpos), -GOAL_WIDTH/2, 0.01)
    glEnd()

# =======================
# PLAYER (HUMANOID)
# =======================
def draw_player(x, y, angle, team_color=(0, 0, 1)):
    glPushMatrix()
    glTranslatef(x, y, 0)
    glRotatef(angle, 0, 0, 1)

    # Body
    glColor3f(*team_color)
    glPushMatrix()
    glScalef(0.6, 0.3, 1.5)
    glutSolidCube(BODY_WIDTH)
    glPopMatrix()

    # Head
    glColor3f(1, 0.8, 0.6)
    glPushMatrix()
    glTranslatef(0, 0, BODY_HEIGHT/2 + HEAD_RADIUS)
    glutSolidSphere(HEAD_RADIUS, 20, 20)
    glPopMatrix()

    # Arms
    glColor3f(*team_color)
    glPushMatrix()
    glTranslatef(BODY_WIDTH/2, 0, BODY_HEIGHT/2 - 5)
    glScalef(0.4, 0.2, 1.0)
    glutSolidCube(ARM_LENGTH)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(-BODY_WIDTH/2, 0, BODY_HEIGHT/2 - 5)
    glScalef(0.4, 0.2, 1.0)
    glutSolidCube(ARM_LENGTH)
    glPopMatrix()

    # Legs
    glColor3f(*team_color)
    glPushMatrix()
    glTranslatef(BODY_WIDTH/4, 0, -BODY_HEIGHT/2)
    glScalef(0.3, 0.3, 1.2)
    glutSolidCube(LEG_LENGTH)
    glPopMatrix()

    glPushMatrix()
    glTranslatef(-BODY_WIDTH/4, 0, -BODY_HEIGHT/2)
    glScalef(0.3, 0.3, 1.2)
    glutSolidCube(LEG_LENGTH)
    glPopMatrix()

    glPopMatrix()

# =======================
# BALL
# =======================
def draw_ball(x, y):
    glColor3f(1, 1, 1)  # White ball
    glPushMatrix()
    glTranslatef(x, y, BALL_RADIUS)
    glutSolidSphere(BALL_RADIUS, 20, 20)
    glPopMatrix()

# =======================
# CONTROLS
# =======================
def special_keys(key, x, y):
    global player_x, player_y, player_angle, ball_x, ball_y
    if key == GLUT_KEY_UP:
        player_y += PLAYER_SPEED
    elif key == GLUT_KEY_DOWN:
        player_y -= PLAYER_SPEED
    elif key == GLUT_KEY_LEFT:
        player_x -= PLAYER_SPEED
        player_angle = 90
    elif key == GLUT_KEY_RIGHT:
        player_x += PLAYER_SPEED
        player_angle = -90

    # Ball interaction (kick if close)
    dx, dy = ball_x - player_x, ball_y - player_y
    dist = math.sqrt(dx*dx + dy*dy)
    if dist < 50:
        ball_x += dx * 0.5
        ball_y += dy * 0.5

    glutPostRedisplay()

# =======================
# DISPLAY
# =======================
def display():
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glLoadIdentity()

    # Camera setup
    gluLookAt(0, -1000, 600, 0, 0, 0, 0, 0, 1)

    # Draw objects
    draw_field()
    draw_player(player_x, player_y, player_angle)
    draw_ball(ball_x, ball_y)

    glutSwapBuffers()

# =======================
# MAIN
# =======================
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(WINDOW_WIDTH, WINDOW_HEIGHT)
    glutCreateWindow(b"GoalGlide 3D_SdRoCk")

    glEnable(GL_DEPTH_TEST)

    glutDisplayFunc(display)
    glutSpecialFunc(special_keys)

    glClearColor(0, 0.6, 0, 1)  # Background green
    glutMainLoop()

if __name__ == "__main__":
    main()
