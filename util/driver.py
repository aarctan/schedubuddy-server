from permutation import permute_classes
from draw_sched import draw_schedule

basic_schedules1 = permute_classes(["CMPUT 355", "CMPUT 397", "PSYCO 223", "PSYCO 258", "PSYCO 275"])
b_s1 = basic_schedules1[0]

basic_schedules2 = permute_classes(["CHEM 102"])
b_s2 = basic_schedules2[3]

mwf_offset = 0
tf_offset = 0
manual_sched1 = (( ['LEC', 'A1', 'REMOTE', 'Melis Gedik', 480+60*mwf_offset, 530+60*mwf_offset, 'MWF', None, 'CHEM 102', '75282'],
['LAB', 'W6', 'REMOTE', 'Yoram Apelblat', 480+90*tf_offset, 650+90*tf_offset, 'T', None, 'CHEM 102', '86592']),)


draw_schedule(b_s1)


