NOTICES OF THE RELEASES v1.00:

1. There are two versions of the program, named run.py and run_pro.py. Simply run any of the program using python2. The difference between run and run_pro is that in run_pro, there is a plotting of the power over time, so it might help in any fibre/anything coupling. The program run_pro_real is displaying the real data queried from the device without anything averaging, i.e read point 3 in "some important notes" below.

2. The program run_pro runs with some of the newer version of numpy and matplotlib, and it might not work on every computers. Also, it takes a lot of OS memory to run run_pro, so you might consider not using it in slow computers.


Some bugs:

1. Sometimes the powermeter gives silly values. This is because the serial connection is not closed/opened properly. Simply unplug and plug in the powermeter again


Some important notes regarding the data acquisition:

1. Each query to the device takes approximately 3 ms. In the program this is performed non-stop. If this slows the performance of the OS considerably, you can probably add time.sleep() in the workerThread1_OPM function.

2. The display on the GUI refreshes over approx. 100 ms (or slower depending on OS). You can change this number in the global variable REFRESH_RATE

3. The average value is calculated with the formula: new_value = ( (NUM_OF_AVG - 1)*old_value + query_value ) / NUM_OF_AVG. So, it is kind of "exponential" average. This is to smoothen down the display value to ease out our eyes. The default value is set to be NUM_OF_AVG = 50, which also means the exponential average time constant is around 150 ms. If you don't like this function, just modify accordingly in the workerThread1_OPM function.

4. The history of average values is erased whenever the range is changed, and the program will start from the newest value. Please wait for the device reading to stabilise in the small time (1-2 time constant) after the change of range.

