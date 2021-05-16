from io import BytesIO
#from sched_gen import generate_schedules
from PIL import Image, ImageDraw, ImageFont
from math import floor, ceil

RED = (255,153,153)
YELLOW = (255,255,153)
GREEN = (153,255,153)
BLUE = (153,204,255)
PURPLE = (204,153,255)
PINK = (255,153,204)
TURQUOISE = (153,255,204)
ORANGE = (255,204,153)
DARKBLUE = (153,153,255)
CYAN = (204,255,255)
HOUR_PADDING = 1

left_margin_offset = 148
top_margin_offset = 90
box_width = 200
vertical_length_50 = 101

color_scheme = (RED, YELLOW, GREEN, BLUE, PURPLE, PINK, TURQUOISE, ORANGE, DARKBLUE, CYAN)
day_lookup = {'U': 0, 'M':1, 'T':2, 'W':3, 'R':4, 'F':5, 'S':6}

font = ImageFont.truetype("fonts/tahoma.ttf", 19)

def get_draw_text(course_class, location=''):
    course_name = course_class[5]
    class_component = course_class[0]
    class_section = course_class[1]
    class_id = course_class[6]
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

#    write "ONLINE" if it's an online class
#    location = course_class[7] if course_class[7] else course_class[2]
    location = location  if location else ''
    text = course_name + '\n' + class_component + ' ' + class_section +\
        ' (' + class_id + ')\n' + location + '\n' + instructor_text
    return text.upper()

def draw_schedule(sched):
    image = Image.open("boilerplate_full.png")
    draw = ImageDraw.Draw(image)
    min_y = 2147483647
    max_y = -2147483648
    class_on_weekend = False
    course_itr = 0
    curr_course = None
    for course_class in sched:
        course_id = course_class[5]
        if course_id != curr_course:
            color = color_scheme[course_itr%len(color_scheme)]
            curr_course = course_id
            course_itr += 1
        for classtime in course_class[4]:
            start_t, end_t, days, location = classtime
            max_y = max(max_y, end_t)
            min_y = min(min_y, start_t)
            if end_t == -1: # Asynchronous classes
                continue
            for day in days:
                if day == 'S' or day == 'U':
                    class_on_weekend = True
                r_x0 = left_margin_offset + day_lookup[day] * box_width + day_lookup[day]*2
                r_x1 = r_x0 + box_width-1

                assert start_t % 15 == 0, "Start time must be a multiple of 15 minutes"
                quarters_past = start_t//15
                quarters_fill = ceil((end_t - start_t) / 15)
                r_y0 = top_margin_offset + quarters_past*25.25 + (quarters_past/4) * 3
                r_y1 = r_y0 + quarters_fill*25.25 + (quarters_fill/4 - 1) * 3

                draw.rectangle([(r_x0-2, r_y0-2), (r_x1+2, r_y1+2)], fill=(0,0,0))
                draw.rectangle([(r_x0, r_y0), (r_x1, r_y1)], fill = color)
                location = location if location else course_class[2]
                draw.text((r_x0+4, r_y0+2), get_draw_text(course_class, location=location), (0,0,0), font=font)

    # get the y region
    boilerplate_width, boilerplate_height = image.size
    top_hours = min(8, floor(min_y/60))
    y_region_top = top_margin_offset + top_hours * vertical_length_50 + top_hours*3
    bottom_hours = (ceil(max_y/60) + HOUR_PADDING)
    y_region_bottom = top_margin_offset + bottom_hours * vertical_length_50 + bottom_hours*3
    y_region = image.crop((0, y_region_top, boilerplate_width, y_region_bottom))
    y_region_length = y_region_bottom-y_region_top
    # paste the y region
    image.paste(y_region, (0, top_margin_offset, boilerplate_width, top_margin_offset+y_region_length))
    y_crop_line = top_margin_offset + y_region_length
    draw.line((0,y_crop_line-2, boilerplate_width, y_crop_line-2), fill=(0, 0, 0), width=2)
    image = image.crop((0, 0, boilerplate_width, y_crop_line))
    # crop weekend if no classes
    if not class_on_weekend:
        x_region_left = left_margin_offset + box_width + 2
        x_region_right = boilerplate_width - box_width - 2
        x_region_length = x_region_right - x_region_left
        x_region = image.crop((x_region_left, 0, x_region_right, y_crop_line))
        image.paste(x_region, (left_margin_offset, 0, left_margin_offset+x_region_length, y_crop_line))
        image = image.crop((0, 0, left_margin_offset + x_region_length, y_crop_line))
    image.save("schedule.png")
    return image

'''
from sched_gen import generate_schedules
(s, a) = generate_schedules(["CMPUT 174", "MATH 117", "MATH 127", "STAT 151", "WRS 101"])
import time
for i in range(len(s)-1):
    draw_schedule(s[i])
    time.sleep(1)
'''


'''
s = (['LEC', 'X01', 'MAIN', None, [\
    (480, 480+90, 'M', 'HC 2-12'),\
    (480+90, 480+90+90, 'M', 'HC 2-12'),\
    (480, 480+170, 'W', 'HC 2-12'),\
    (480, 480+110, 'F', 'HC 2-12')], 'JAPAN 101', '51778'],)

print(s)
draw_schedule(s)
'''

#s = [['LEC', 'A1', 'MAIN', None, [(540, 650, 'F', None), (540, 650, 'W', None)], 'CMPUT 401', '56366'], ['SEM', 'F1', 'MAIN', None, [(1020, 1260, 'F', None), (540, 590, 'M', None)], 'CMPUT 401', '56367'], ['LAB', 'D01', 'MAIN', None, [(540, 960, 'US', None)], 'CMPUT 401', '56368']]
#draw_schedule(s)