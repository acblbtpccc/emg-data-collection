#if defined(ARDUINO) && ARDUINO >= 100
#include "Arduino.h"
#else
#include "WProgram.h"
#endif

#include "EMGFilters.h"

#define TIMING_DEBUG 1

#define SensorInputPinA1 A1 // input pin number for first sensor
#define SensorInputPinA2 A2 // input pin number for second sensor

#define SAMPLE_FREQ_500HZ 500
#define TARGET_FREQ 30
#define SAMPLES_PER_WINDOW (SAMPLE_FREQ_500HZ / TARGET_FREQ) 

EMGFilters myFilterA1;
EMGFilters myFilterA2;

int sampleRate = SAMPLE_FREQ_500HZ;

int humFreq = NOTCH_FREQ_50HZ;
static int Threshold = 100;

unsigned long timeStamp;
unsigned long timeBudget;

int sampleCounter = 0;
long sumOfSquaresA1 = 0;
long sumOfSquaresA2 = 0;

void setup() {
    /* add setup code here 所有三种滤波器（陷波、低通、高通）都被激活*/
    myFilterA1.init(sampleRate, humFreq, true, true, true);
    myFilterA2.init(sampleRate, humFreq, true, true, true);

    // open serial 初始化串口通信，波特率设置为115200
    Serial.begin(115200);

    // setup for time cost measure
    // using micros() 计算每个采样周期允许的最大微秒数，用于确保ADC采样频率与设定的采样频率一致
    timeBudget = 1e6 / sampleRate;
    // micros will overflow and auto return to zero every 70 minutes
}

void loop() {
    // Measure the time in microseconds at the start of the loop
    timeStamp = micros();

    int ValueA1 = analogRead(SensorInputPinA1);
    int ValueA2 = analogRead(SensorInputPinA2);

    // Filter processing
    int DataAfterFilterA1 = myFilterA1.update(ValueA1);
    int DataAfterFilterA2 = myFilterA2.update(ValueA2);
    
    // Calculate the square of the filtered signal to extract the signal envelope
    int envelopeA1 = sq(DataAfterFilterA1);
    int envelopeA2 = sq(DataAfterFilterA2);
    
    // Threshold filtering
    envelopeA1 = (envelopeA1 > Threshold) ? envelopeA1 : 0;
    envelopeA2 = (envelopeA2 > Threshold) ? envelopeA2 : 0;

    sumOfSquaresA1 += envelopeA1;
    sumOfSquaresA2 += envelopeA2;
    sampleCounter++;

    if (sampleCounter >= SAMPLES_PER_WINDOW){
        float rmsA1 = sqrt((float)sumOfSquaresA1 / SAMPLES_PER_WINDOW);
        float rmsA2 = sqrt((float)sumOfSquaresA2 / SAMPLES_PER_WINDOW);
        
        // Print both RMS values on the same line separated by a comma
        Serial.print(rmsA1);
        Serial.print(",");
        Serial.println(rmsA2);
        
        // Reset the sums and counter
        sumOfSquaresA1 = 0; 
        sumOfSquaresA2 = 0; 
        sampleCounter = 0;
    }

    // Measure time spent in the loop
    unsigned long timeSpent = micros() - timeStamp;
    if (timeSpent < timeBudget) {
        delayMicroseconds(timeBudget - timeSpent);
    }
}
