from PIL import Image, ImageDraw, ImageFont
from math import ceil

RED = (255,153,153)
YELLOW = (254,255,153)
GREEN = (153,255,152)
BLUE = (153,204,254)
PURPLE = (204,153,255)
PINK = (255,153,204)
HOUR_PADDING = 2

left_margin_offset = 148
top_margin_offset = 90
box_width = 200
vertical_length_50 = 101

color_scheme = (RED, YELLOW, GREEN, BLUE, PURPLE, PINK)
day_lookup = {'U': 0, 'M':1, 'T':2, 'W':3, 'R':4, 'F':5, 'S':6}
length_lookup = {
    0:      0,
    30:     51,
    50:     vertical_length_50,
    80:     154,
    110:    101,
    170:    309,
    180:    309,
}
font = ImageFont.truetype("fonts/tahoma.ttf", 22)

def get_draw_text(course_class):
    course_name = course_class[8]
    class_component = course_class[0]
    class_section = course_class[1]
    class_id = course_class[9]
    instructor = course_class[3]
    instructor_text = ''
    if instructor:
        instructor_full = instructor.split()
        instructor_initials = []
        for i in range(len(instructor_full)-1):
            instructor_initials.append(instructor_full[i][0].upper() + '. ')
        instructor_text = ''.join(instructor_initials) + instructor_full[-1]
        if font.getsize(instructor_text)[0] > box_width-3: # pop until fit with elipses
            while font.getsize(instructor_text + '...')[0] > box_width-3:
                instructor_text = instructor_text[:-1]
            instructor_text += '...'
        instructor_text_size = font.getsize(instructor_text)
    location = course_class[2]
    text = course_name + '\n' + class_component + ' ' + class_section +\
        ' (' + class_id + ')\n' + instructor_text
    return text.upper()

def draw_schedule(sched):
    with Image.open("boilerplate_full.png") as image:
        draw = ImageDraw.Draw(image)
        colors = 0
        min_y = 2147483647
        max_y = -2147483648
        for course in sched:
            color = color_scheme[colors%6]
            for course_class in course:
                start_t, end_t = course_class[4], course_class[5]
                max_y = max(max_y, end_t)
                min_y = min(min_y, start_t)
                if end_t == -1: # Asynchronous classes
                    continue
                days = course_class[6]
                for day in days:               
                    r_x0 = left_margin_offset + day_lookup[day] * box_width + day_lookup[day]*2
                    r_x1 = r_x0 + box_width-1

                    r_y0 = top_margin_offset
                    hours = (start_t // 60)
                    minutes = (start_t % 60)
                    bars_past = 0

                    if start_t % 60 == 0:
                        r_y0 += hours*vertical_length_50 + hours*3
                    elif (start_t % 90-30) == 0:
                        r_y0 += length_lookup[minutes]
                        incr_90 = start_t // 90
                        r_y0 += incr_90*length_lookup[80] + incr_90*2
                    '''
                    if day in 'MWF':
                        bars_past = max(0, hours*3-1)
                    elif day in 'TR':
                        tr_offset = (start_t)//90
                        bars_past = max(0, tr_offset*2+tr_offset-1)
                    r_y0 = top_margin_offset + hours*vertical_length_50 + bars_past
                    r_y0 += length_lookup[minutes]
                    if hours > 0: # Manual y offset adjust 
                        r_y0 += 1
                    '''

                    r_y1 = r_y0 + length_lookup[end_t - start_t]
                    draw.rectangle([(r_x0-2, r_y0-2), (r_x1+2, r_y1+2)], fill=(0,0,0))
                    draw.rectangle([(r_x0, r_y0), (r_x1, r_y1)], fill = color)
                    draw.text((r_x0+2, r_y0+2), get_draw_text(course_class), (0,0,0), font=font)
                    
            colors += 1
        w,h = image.size
        hours_cropped = 24-(ceil(max_y/60) + HOUR_PADDING)
        crop_line = h - (hours_cropped*vertical_length_50 + hours_cropped*3)
        draw.line((0,crop_line-2, w, crop_line-2), fill=(0, 0, 0), width=2)
        image.crop((0, 0, w, crop_line)).save("schedule.png")
