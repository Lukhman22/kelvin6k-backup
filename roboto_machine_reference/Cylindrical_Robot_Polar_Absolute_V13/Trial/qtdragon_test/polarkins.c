/*
 * polarkins.c - Polar Kinematics for LinuxCNC 2.9
 * Converts Cartesian X,Y to polar angle,radius
 * 
 * Allows continuous angle motion (no wrapping to 0-360)
 * This prevents abrupt jumps when crossing quadrant boundaries
 */

#include "kinematics.h"
#include "rtapi_math.h"
#include "rtapi.h"
#include "rtapi_app.h"
#include "hal.h"

#define MIN_RADIUS 10.0  // Minimum radius to avoid singularity at center

MODULE_LICENSE("GPL");

// Store previous angle to allow continuous motion
static double prev_angle = 0.0;
static int initialized = 0;

KINEMATICS_TYPE kinematicsType(void) {
    return KINEMATICS_BOTH;
}

int kinematicsSwitchable(void) {
    return 0;
}

int kinematicsSwitch(int switchkins_type) {
    return 0;
}

int kinematicsForward(const double *joints,
                      EmcPose *pos,
                      const KINEMATICS_FORWARD_FLAGS *fflags,
                      KINEMATICS_INVERSE_FLAGS *iflags) {
    
    double angle_rad = joints[0] * (M_PI / 180.0);
    double radius = joints[1];
    
    // Polar to Cartesian
    pos->tran.x = radius * cos(angle_rad);
    pos->tran.y = radius * sin(angle_rad);
    pos->tran.z = 0;
    pos->a = 0;
    pos->b = 0;
    pos->c = 0;
    pos->u = 0;
    pos->v = 0;
    pos->w = 0;
    
    return 0;
}

int kinematicsInverse(const EmcPose *pos,
                      double *joints,
                      const KINEMATICS_INVERSE_FLAGS *iflags,
                      KINEMATICS_FORWARD_FLAGS *fflags) {
    
    double x = pos->tran.x;
    double y = pos->tran.y;
    
    // Calculate radius
    double radius = sqrt(x*x + y*y);
    
    // Handle near-center singularity
    if (radius < MIN_RADIUS) {
        // Near center - keep previous angle, set minimum radius
        joints[0] = prev_angle;
        joints[1] = radius;
        return 0;
    }
    
    // Calculate new angle (-180 to +180)
    double angle_deg = atan2(y, x) * (180.0 / M_PI);
    
    if (initialized) {
        // Find the closest equivalent angle to avoid jumps
        // Add/subtract 360 to find the angle closest to prev_angle
        double diff = angle_deg - prev_angle;
        
        // Normalize difference to -180 to +180
        while (diff > 180.0) diff -= 360.0;
        while (diff < -180.0) diff += 360.0;
        
        // Apply the normalized difference
        angle_deg = prev_angle + diff;
    } else {
        initialized = 1;
    }
    
    prev_angle = angle_deg;
    
    joints[0] = angle_deg;
    joints[1] = radius;
    
    return 0;
}

int kinematicsHome(EmcPose *world,
                   double *joints,
                   KINEMATICS_FORWARD_FLAGS *fflags,
                   KINEMATICS_INVERSE_FLAGS *iflags) {
    *fflags = 0;
    *iflags = 0;
    
    // Reset angle tracking on home
    prev_angle = joints[0];
    initialized = 1;
    
    return kinematicsForward(joints, world, fflags, iflags);
}

static int comp_id;

int rtapi_app_main(void) {
    comp_id = hal_init("polarkins");
    if (comp_id < 0) return comp_id;
    hal_ready(comp_id);
    return 0;
}

void rtapi_app_exit(void) {
    hal_exit(comp_id);
}

EXPORT_SYMBOL(kinematicsType);
EXPORT_SYMBOL(kinematicsSwitchable);
EXPORT_SYMBOL(kinematicsSwitch);
EXPORT_SYMBOL(kinematicsForward);
EXPORT_SYMBOL(kinematicsInverse);
EXPORT_SYMBOL(kinematicsHome);
