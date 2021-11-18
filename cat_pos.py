import sys
with open(sys.argv[1], 'r') as logs_data:
    lines = logs_data.read().splitlines()
with open("catched.txt", "w") as catched_file:
    for line in lines:
        if line.startswith("(<droidlet.shared_data_structs.RGBDepth object"):
            catched_file.write(line + '\n')
