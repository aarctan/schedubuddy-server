from PIL import Image, ImageDraw, ImageFont
from math import floor, ceil

RED = (255,153,153)
YELLOW = (254,255,153)
GREEN = (153,255,152)
BLUE = (153,204,254)
PURPLE = (204,153,255)
PINK = (255,153,204)
HOUR_PADDING = 0

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
    240:    414,
    420:    725,
}
font = ImageFont.truetype("fonts/tahoma.ttf", 19)

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
        ' (' + class_id + ')\n' + location + '\n' + instructor_text
    return text.upper()

def draw_schedule(sched):
    with Image.open("boilerplate_full.png") as image:
        draw = ImageDraw.Draw(image)
        colors = 0
        min_y = 2147483647
        max_y = -2147483648
        class_on_weekend = False
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
                    if day == 'S' or day == 'U':
                        class_on_weekend = True
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
                
                    r_y1 = r_y0 + length_lookup[end_t - start_t]
                    draw.rectangle([(r_x0-2, r_y0-2), (r_x1+2, r_y1+2)], fill=(0,0,0))
                    draw.rectangle([(r_x0, r_y0), (r_x1, r_y1)], fill = color)
                    draw.text((r_x0+4, r_y0+2), get_draw_text(course_class), (0,0,0), font=font)
            colors += 1

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
