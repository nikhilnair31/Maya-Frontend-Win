from monitorcontrol import get_monitors

def switch_to_laptop():
    try:
        found = False
        for monitor in get_monitors():
            found = True
            with monitor:
                # Try to detect what the monitor currently thinks it is
                try:
                    current_input = monitor.get_input_source()
                    print(f"Monitor detected! Current input source code is: {current_input}")
                except:
                    print("Monitor detected, but could not read current input.")

                # LG Common Codes: 
                # HDMI1=17, HDMI2=18, USB-C/DP=19, DP=15
                target_code = 16
                print(f"Attempting to set input to {target_code}...")
                monitor.set_input_source(target_code)
        
        if not found:
            print("No monitors found. Is DDC/CI enabled in the monitor's menu?")
            
    except Exception as e:
        print(f"Monitor Control Error: {e}")

if __name__ == "__main__":
    # Running this directly will help you debug
    switch_to_laptop()