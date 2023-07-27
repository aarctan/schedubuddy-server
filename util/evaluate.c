#include <stdlib.h>
#include <math.h>
#include <stdio.h>

// adjustable modifiers
#define WEIGHT_START_TIME_ERR 2
#define WEIGHT_START_TIME_VARIANCE 2
#define WEIGHT_END_TIME_VARIANCE 1
#define WEIGHT_GAP_ERR 4
#define WEIGHT_TIME_WASTED 3
#define SMALL_BLOCK_DIR_MODIFIER (7 / 10)

// non-adjustable macros
#define MAX_BLOCKS_IN_DAY 48
#define NUM_DAYS 7
#define MAX_ERROR_UNITS 10
#define WEIGHT_SUM ((WEIGHT_GAP_ERR) + (WEIGHT_TIME_WASTED) + (WEIGHT_START_TIME_ERR) + (WEIGHT_START_TIME_VARIANCE) + (WEIGHT_END_TIME_VARIANCE))

typedef struct
{
    int Day;
    int Start;
    int End;
} Block;

typedef struct
{
    int Start;
    int End;
} Range;

typedef struct
{
    float startTime;
    float startTimeVariance;
    float endTimeVariance;
    float gapError;
    float timeWasted;
} Metrics;

// qsort comparator for sorting ranges
int __compareRange(const void *a, const void *b)
{
    return ((Range *)a)->Start - ((Range *)b)->Start;
}

float __mean(float arr[NUM_DAYS])
{
    float sum = 0;
    int count = 0;
    float mean = 0;
    for (int i = 0; i < NUM_DAYS; ++i) {
        if (arr[i] != -1) {
            sum += arr[i];
            ++count;
        }
    }
    return (float)(sum / count);
}

float __variance(int arr[NUM_DAYS])
{
    int sum = 0;
    int count = 0;
    float mean = 0;
    float variance = 0;
    for (int i = 0; i < NUM_DAYS; ++i) {
        if (arr[i] != -1) {
            sum += arr[i];
            ++count;
        }
    }
    mean = (float)(sum / count);
    for (int i = 0; i < NUM_DAYS; ++i) {
        if (arr[i] != -1)
            variance += (arr[i] - mean) * (arr[i] - mean);
    }
    variance = variance / count;
    return variance;
}

/*
 * Build a blocks grid, e.g
 * M             W           F
 * (100, 150)    (100, 150)  (400, 470)
 * (400, 470)
 * Then sort the ranges and coalesce the blocks where the gap is <= 15
 */
float evaluate(Block p[],
               size_t numBlocks,
               int consecLecPref,
               int startTimePref,
               int commuteTime)
{
    Range blocks[NUM_DAYS][MAX_BLOCKS_IN_DAY] = {0};
    int blockCnt[NUM_DAYS] = {0};
    int coalescedBlockCnt[NUM_DAYS] = {0};

    for (size_t i = 0; i < numBlocks; ++i) {
        int day = p[i].Day;
        Range currRange = {p[i].Start, p[i].End};
        blocks[day][blockCnt[day]++] = currRange;
    }

    for (int day = 0; day < NUM_DAYS; ++day) {
        int numBlocksInDay = blockCnt[day];
        if (numBlocksInDay <= 1) {
            coalescedBlockCnt[day] = numBlocksInDay;
            continue;
        }
        qsort(blocks[day], numBlocksInDay, sizeof(Range), __compareRange);
        int currBlock = 0;
        for (int i = 1; i < numBlocksInDay; ++i) {
            if (blocks[day][i].Start - blocks[day][currBlock].End <= 15)
                blocks[day][currBlock].End = blocks[day][i].End;
            else
                blocks[day][++currBlock] = blocks[day][i];
        }
        coalescedBlockCnt[day] = currBlock + 1;
    }

#define EMPTY_ARR {-1, -1, -1, -1, -1, -1, -1}
    Metrics scores;
    unsigned timeWasted = 0;
    int startTimes[NUM_DAYS] = EMPTY_ARR;
    int endTimes[NUM_DAYS] = EMPTY_ARR;
    float startTimesScore[NUM_DAYS] = EMPTY_ARR;
    int numDaysWithClass = 0;
    float gapErrSum = 0.0;
    for (int day = 0; day < NUM_DAYS; ++day) {
        if (coalescedBlockCnt[day] == 0)
            continue;

        ++numDaysWithClass;
        timeWasted += commuteTime * 2;
        int dayStart = blocks[day][0].Start;
        int dayEnd = blocks[day][coalescedBlockCnt[day] - 1].End;
        startTimes[day] = dayStart;
        endTimes[day] = dayEnd;

        // For every quarter hour away from the ideal start time for this day, subtract half a point.
        // If the ideal start is 10:00 AM and the first Monday class is 1:15PM, Monday gets 3.5/10.
        float dayStartScore = fmax(1.0, 10.0 - round(abs(startTimePref - dayStart) / 15) * 0.25);
        startTimesScore[day] = dayStartScore;

        // Block gap calculation is generally the most important metric.
        // TODO: experiment with allowing the day with most gap error to be removed from the error sum.
        //       Often a schedule has one crammed day to ease the load on every other day.
        for (int i = 0; i < coalescedBlockCnt[day]; ++i) {
            float blockLen = blocks[day][i].End - blocks[day][i].Start;
            float blockGap = abs(consecLecPref - blockLen) / 30.0;
            // if the block is shorter than the ideal block length, soften the penalty by multipliying by the modifier.
            // The main goal of this metric is to penalize gigantic blocks.
            if (blockLen < consecLecPref) {
                blockGap *= SMALL_BLOCK_DIR_MODIFIER;
            }
            gapErrSum += fmin(pow(blockGap, 7/5), pow(MAX_ERROR_UNITS, 7/5));
        }
      
    }
    scores.timeWasted = fmax(1.0, 10.0 - (timeWasted / 15) * 0.125);
    scores.gapError = 10.0 - sqrt(gapErrSum);
    scores.startTime = __mean(startTimesScore);

    // We track the variance of start and end times of each day, such that the best schedule has the minimal amount of
    // variance of start times per day and also ends at approximately the same time every day.
    scores.startTimeVariance = fmax(1.0, 10.0 - sqrt(__variance(startTimes)) / 100);
    scores.endTimeVariance = fmax(1.0, 10.0 - sqrt(__variance(endTimes)) / 100);

    float score = (scores.startTime * WEIGHT_START_TIME_ERR +
                   scores.startTimeVariance * WEIGHT_START_TIME_VARIANCE +
                   scores.endTimeVariance * WEIGHT_END_TIME_VARIANCE +
                   scores.gapError * WEIGHT_GAP_ERR +
                   scores.timeWasted * WEIGHT_TIME_WASTED ) /
                  WEIGHT_SUM;

    return score;
}
