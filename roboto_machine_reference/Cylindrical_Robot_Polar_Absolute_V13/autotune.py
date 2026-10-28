#!/usr/bin/env python3
"""
Motor Auto-Tuning Script for Polar Robot
Tests motor response and suggests optimal settings
"""

import hal
import time
import math

class AutoTuner:
    def __init__(self):
        self.h = hal.component("autotuner")
        
        # Inputs - motor feedback
        self.h.newpin("pos-fb", hal.HAL_FLOAT, hal.HAL_IN)
        self.h.newpin("pos-cmd", hal.HAL_FLOAT, hal.HAL_IN)
        
        # Output - test command
        self.h.newpin("test-cmd", hal.HAL_FLOAT, hal.HAL_OUT)
        self.h.newpin("running", hal.HAL_BIT, hal.HAL_OUT)
        
        self.h.ready()
        
        self.errors = []
        self.max_error = 0
        self.oscillations = 0
    
    def test_step_response(self, step_size=10, duration=2.0):
        """Send step command and measure response"""
        print(f"\n=== Step Response Test (step={step_size}) ===")
        
        start_pos = self.h['pos-fb']
        target = start_pos + step_size
        
        self.h['test-cmd'] = target
        self.h['running'] = True
        
        samples = []
        start_time = time.time()
        
        while time.time() - start_time < duration:
            fb = self.h['pos-fb']
            error = target - fb
            samples.append((time.time() - start_time, fb, error))
            time.sleep(0.01)
        
        self.h['running'] = False
        
        # Analyze response
        return self.analyze_response(samples, target)
    
    def analyze_response(self, samples, target):
        """Analyze step response for tuning"""
        errors = [s[2] for s in samples]
        positions = [s[1] for s in samples]
        
        # Max overshoot
        max_pos = max(positions)
        final_pos = positions[-1] if positions else 0
        overshoot = max_pos - target if max_pos > target else 0
        overshoot_pct = (overshoot / abs(target - positions[0])) * 100 if positions else 0
        
        # Settling time (within 2% of final value)
        settle_threshold = abs(target - positions[0]) * 0.02
        settle_time = None
        for t, pos, err in samples:
            if abs(pos - target) < settle_threshold:
                settle_time = t
                break
        
        # Count oscillations
        oscillations = 0
        prev_err = 0
        for err in errors:
            if prev_err * err < 0:  # Sign change
                oscillations += 1
            prev_err = err
        
        # Final error
        final_error = abs(errors[-1]) if errors else 0
        
        results = {
            'overshoot_pct': overshoot_pct,
            'settle_time': settle_time,
            'oscillations': oscillations // 2,  # Count full cycles
            'final_error': final_error,
            'max_error': max(abs(e) for e in errors) if errors else 0
        }
        
        print(f"  Overshoot: {overshoot_pct:.1f}%")
        print(f"  Settle time: {settle_time:.2f}s" if settle_time else "  Settle time: >2s")
        print(f"  Oscillations: {results['oscillations']}")
        print(f"  Final error: {final_error:.3f}")
        
        return results
    
    def suggest_tuning(self, results):
        """Suggest tuning changes based on response"""
        print("\n=== Tuning Suggestions ===")
        
        if results['oscillations'] > 2:
            print("⚠️  HIGH OSCILLATION - Motor is vibrating")
            print("   → Reduce MAX_ACCELERATION in INI file")
            print("   → Reduce drive H09.15 (Position gain)")
            print("   → Increase FERROR tolerance")
        
        if results['overshoot_pct'] > 20:
            print("⚠️  HIGH OVERSHOOT")
            print("   → Reduce MAX_VELOCITY")
            print("   → Reduce drive H09.00 (Speed gain)")
        
        if results['settle_time'] and results['settle_time'] > 1.0:
            print("⚠️  SLOW RESPONSE")
            print("   → May need higher gains (carefully)")
        
        if results['final_error'] > 1.0:
            print("⚠️  POSITION ERROR")
            print("   → Check encoder scale factor")
            print("   → Check for mechanical issues")
        
        if (results['oscillations'] <= 2 and 
            results['overshoot_pct'] < 10 and 
            results['final_error'] < 0.5):
            print("✓  Motor response looks GOOD!")
    
    def run_full_test(self):
        """Run complete tuning test"""
        print("\n" + "="*50)
        print("       POLAR ROBOT AUTO-TUNING TEST")
        print("="*50)
        
        print("\nMake sure:")
        print("  1. LinuxCNC is running")
        print("  2. Machine is homed")
        print("  3. Motors are enabled")
        print("  4. Robot is in safe position")
        
        input("\nPress ENTER to start test...")
        
        # Test with small step
        results = self.test_step_response(step_size=5)
        self.suggest_tuning(results)
        
        print("\n" + "="*50)
        print("Test complete. Apply suggested changes and retest.")
        print("="*50)

def main():
    print("""
╔═══════════════════════════════════════════════════╗
║     SIMPLE MANUAL TUNING GUIDE                    ║
╠═══════════════════════════════════════════════════╣
║                                                   ║
║  If motor VIBRATES:                               ║
║    1. Reduce MAX_ACCELERATION in INI (try 50)    ║
║    2. Reduce MAX_VELOCITY (try 30)               ║
║    3. Increase FERROR (try 1000)                 ║
║                                                   ║
║  Current recommended settings for vibrating motor:║
║                                                   ║
║  [JOINT_0]                                        ║
║  MAX_VELOCITY = 30.0                              ║
║  MAX_ACCELERATION = 50.0                          ║
║  FERROR = 1000.0                                  ║
║  MIN_FERROR = 200.0                               ║
║                                                   ║
║  Or adjust on drive (SV660):                      ║
║  H09.15 = lower value (try 50% of current)        ║
║  H09.00 = lower value (try 50% of current)        ║
║                                                   ║
╚═══════════════════════════════════════════════════╝
""")

if __name__ == '__main__':
    main()
