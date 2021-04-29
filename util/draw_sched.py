from PIL import Image, ImageDraw

left_margin_offset = 75
top_margin_offset = 45
box_width = 103
vertical_length_50 = 49
vertical_length_80 = 75

RED = (255,153,153)
YELLOW = (254,255,153)
GREEN = (153,255,152)
BLUE = (153,204,254)
PURPLE = (204,153,255)
PINK = (255,153,204)

color_scheme = (RED, YELLOW, GREEN, BLUE, PURPLE, PINK)
day_lookup = {'M':0, 'T':1, 'W':2, 'R':3, 'F':4, 'S':5, 'U':6}
length_lookup = {50:vertical_length_50, 80:vertical_length_80}

def draw_schedule(sched):
    with Image.open("../boilerplate.png") as image:
        draw = ImageDraw.Draw(image)
        colors = 0
        for course in sched:
            color = color_scheme[colors%6]
            for course_class in course:
                days = course_class[6]
                for day in days:                    
                    start_t, end_t = course_class[4], course_class[5]
                    r_x0 = left_margin_offset + day_lookup[day] * box_width + day_lookup[day]*2
                    r_y0 = 0
                    if start_t % 60 == 0:
                        hours = (start_t // 60 - 8)
                        r_y0 = top_margin_offset + hours*vertical_length_50 + hours*2
                        if hours > 0: # Manual y offset adjust 
                            r_y0 += 1
                    r_x1 = r_x0 + box_width
                    r_y1 = r_y0 + length_lookup[end_t - start_t]
                    draw.rectangle([(r_x0, r_y0), (r_x1, r_y1)], fill = color)
            colors += 1

        image.save("schedule.png")