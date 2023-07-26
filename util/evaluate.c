#include <stdlib.h>
#include <math.h>

#define MAX_BLOCKS_IN_DAY   48
#define NUM_DAYS            7

typedef struct {
    int Day;
    int Start;
    int End;
} Block;

typedef struct {
    int Start;
    int End;
} Range;

typedef struct {
    int startTime;
    int startTimeVariance;
    int endTimeVariance;
    int gapError;
    int timeWasted;
} Metrics;

// qsort comparator for sorting ranges
int __compareRange(const void* a, const void* b) {
    return ((Range*)a)->Start - ((Range*)b)->Start;
}

float __variance(int arr[NUM_DAYS]) {
    int sum = 0;
    int count = 0;
    float mean = 0;
    float variance = 0;
    for(int i = 0; i < NUM_DAYS; ++i) {
        if (arr[i] != -1) {
            sum += arr[i];
            ++count;
        }
    }
    mean = (float) (sum / count);
    for(int i = 0; i < NUM_DAYS; ++i) {
        if (arr[i] != -1) {
            variance += (arr[i] - mean) * (arr[i] - mean);
        }
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
int evaluate(Block p[],
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
            if (blocks[day][i].Start - blocks[day][currBlock].End <= 15) {
                blocks[day][currBlock].End = blocks[day][i].End;
            } else {
                blocks[day][++currBlock] = blocks[day][i];
            }
        }
        coalescedBlockCnt[day] = currBlock + 1;
    }

    Metrics scores;
    unsigned timeWasted = 0;
    int startTimes[NUM_DAYS] = {-1};
    int endTimes[NUM_DAYS] = {-1};
    int numDaysWithClass = 0;
    for (int day = 0; day < NUM_DAYS; ++day) {
        if (coalescedBlockCnt[day] == 0) {
            continue;
        }
        ++numDaysWithClass;
        timeWasted += commuteTime * 2;
        int dayStart = blocks[day][0].Start;
        int dayEnd = blocks[day][coalescedBlockCnt[day]].End;
        startTimes[day] = dayStart;
        endTimes[day] = dayEnd;
    }
    scores.startTimeVariance = fmax(1.0, 10.0 - sqrt(__variance(startTimes)) * 2);
    scores.endTimeVariance = fmax(1.0, 10.0 - sqrt(__variance(endTimes)) * 2);

    return scores.endTimeVariance;
}
