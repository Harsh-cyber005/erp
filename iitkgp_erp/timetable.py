import requests
from bs4 import BeautifulSoup as bs
import os
import json
import sys
from iitkgp_erp import erp

db_folder = "../lib/db/"
sessionFile = "../lib/session.txt"
lib_folder = "../lib/"
course_names = []
choices = []
labs = []
lab_choices = {}

lab_name_set = set([])
lab_name_map = {}
lab_slots_map = {}
lab_days_with_slots_map = {}

headers = {
    'timeout': '20',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/51.0.2704.79 Chrome/51.0.2704.79 Safari/537.36',
}

def get_timetable(session: requests.Session, log: bool = False):
    if log:
        print("Getting timetable")
    resp = session.get("https://erp.iitkgp.ac.in/Acad/student/student_timetable.jsp", headers=headers, data={"ssoToken": session.cookies.get("ssoToken"),"module_id": 16, "menu_id": 40})
    if resp.status_code != 200:
        if log:
            print("Error in getting timetable")
        return None
    if log:
        print("Timetable received")
    return resp.text

def find_day_timetable(day: str, start: int, end: int, days: list):
    day_timetable = []
    for i in range(start, end):
        slots = days[i].find_all("td")
        final = []
        for slot in slots:
            if day in str(slot):
                continue
            tmp = {
                "code": "",
                "room": "",
                "time": "",
                "rspan": 0,
                "cspan": 0
            }
            if slot.has_attr("rowspan"):
                tmp["rspan"] = int(slot["rowspan"])
            if slot.has_attr("colspan"):
                tmp["cspan"] = int(slot["colspan"])
            b_elem = slot.find("b")
            str_b_elem = str(b_elem)[3:-4]
            if "<br/>" in str_b_elem:
                tmp["code"] = str_b_elem.split("<br/>")[0].strip()
                tmp["room"] = str_b_elem.split("<br/>")[1].strip()
            final.append(tmp)
        day_timetable.append(final)
    return day_timetable

def get_start_end_days(days: list, this_day: str):
    if this_day == "Mon":
        next_day = "Tue"
    elif this_day == "Tue":
        next_day = "Wed"
    elif this_day == "Wed":
        next_day = "Thu"
    elif this_day == "Thu":
        next_day = "Fri"
    start = 0
    ctr = 0
    for day in days:
        if this_day in str(day):
            start = ctr
            break
        ctr += 1
    ctr = 0
    end = -1
    if this_day == "Fri":
        return start, len(days)
    for day in days:
        if next_day in str(day):
            end = ctr
            break
        ctr += 1
    return start, end

def populate_timetable_with_time(day_timetable: list, this_day: str):
    maxspace = find_max_populated_slot(day_timetable)
    data = [
        {
            "time": "08:00 - 08:55",
            "index": 0,
            "items": [],
            "space": maxspace,
            "day": this_day
        },
        {
            "time": "09:00 - 09:55",
            "index": 1,
            "items": [],
            "space": maxspace,
            "day": this_day
        },
        {
            "time": "10:00 - 10:55",
            "index": 2,
            "items": [],
            "space": maxspace,
            "day": this_day
        },
        {
            "time": "11:00 - 11:55",
            "index": 3,
            "items": [],
            "space": maxspace,
            "day": this_day
        },
        {
            "time": "12:00 - 12:55",
            "index": 4,
            "items": [],
            "space": maxspace,
            "day": this_day
        },
        {
            "time": "02:00 - 02:55",
            "index": 5,
            "items": [],
            "space": maxspace,
            "day": this_day
        },
        {
            "time": "03:00 - 03:55",
            "index": 6,
            "items": [],
            "space": maxspace,
            "day": this_day
        },
        {
            "time": "04:00 - 04:55",
            "index": 7,
            "items": [],
            "space": maxspace,
            "day": this_day
        },
        {
            "time": "05:00 - 05:55",
            "index": 8,
            "items": [],
            "space": maxspace,
            "day": this_day
        }
    ]
    for iter in day_timetable:
        start = 0
        for slot in iter:
            rspan = slot["rspan"]
            cspan = slot["cspan"]
            code = slot["code"]
            room = slot["room"]
            for i in range(start,9):
                if data[i]["space"] < rspan:
                    continue
                placeable = True
                for j in range(i,i+cspan):
                    if j > 8:
                        placeable = False
                        break
                    if data[j]["space"] < rspan:
                        placeable = False
                        break
                if placeable:
                    item = {
                        "code":code,
                        "room":room
                    }
                    for j in range(i,i+cspan):
                        if j > 8:
                            break
                        data[j]["items"].append(item)
                        data[j]["space"] -= rspan
                    start = i+cspan
                    break
                else:
                    start = i
                    continue
    data = clean_day_timetable(data)
    data = add_name_to_timetable(data, this_day)
    data = set_choices(data, this_day)
    data = set_labs(data, this_day)
    return data

def find_max_populated_slot(day_timetable: list):
    max_populated = 0
    for i in day_timetable:
        for j in i:
            if j["rspan"] > max_populated:
                max_populated = j["rspan"]
    return max_populated

def get_choices(this_day: str, time: str, code: str):
    global choices
    if choices == []:
        try:
            if not os.path.exists(f"{db_folder}choices.json"):
                with open(f"{db_folder}choices.json", "w") as f:
                    f.write("[]")
            with open (f"{db_folder}choices.json", "r") as f:
                choices = json.load(f)
        except:
            choices = []
            print("Choices file corrupted, try deleting it and running again")
    key_str = this_day + time + code
    for i in choices:
        if i["key"] == key_str:
            return i["choice"]
    return 0

def set_choices(day_timetable: list, this_day: str):
    for slot in day_timetable:
        if len(slot["items"]) > 1:
            choice = get_choices(this_day, slot["time"], slot["items"][0]["code"])
            if choice == 0:
                print("On ", this_day, " at ", slot["time"], " you have the following choices: ")
                for i in range(len(slot["items"])):
                    if slot["items"][i]["room"] == "":
                        print(i+1, ". ", slot["items"][i]["code"] , " - ", slot["items"][i]["name"])
                    else:
                        print(i+1, ". ", slot["items"][i]["code"], " - ", slot["items"][i]["name"] , " - ", slot["items"][i]["room"])
                choice = int(input("Enter your choice (By Default we will keep all of them): "))
                if choice > 0 and choice <= len(slot["items"]):
                    slot["items"] = [slot["items"][choice-1]]
                    choices.append({"key": this_day + slot["time"] + slot["items"][0]["code"], "choice": choice})
                    with open(f"{db_folder}choices.json", "w") as f:
                        f.write(json.dumps(choices))
                else:
                    print("Invalid choice, keeping all of them, will ask again next time")
            else:
                slot["items"] = [slot["items"][choice-1]]
    return day_timetable

def get_labs():
    global labs
    if labs == []:
        try:
            if not os.path.exists(f"{db_folder}labs.json"):
                with open(f"{db_folder}labs.json", "w") as f:
                    f.write("[]")
            with open (f"{db_folder}labs.json", "r") as f:
                labs = json.load(f)
        except:
            labs = []
            print("Labs file corrupted, try deleting it and running again")
    return labs

def set_labs(day_timetable: list, this_day: str):
    map = {
        "Mon": 0,
        "Tue": 1,
        "Wed": 2,
        "Thu": 3,
        "Fri": 4
    }
    global labs
    for slot in day_timetable:
        for i in slot["items"]:
            name:str = i["name"]
            if " LAB" in name.strip().upper() or " DRAWING" in name.strip().upper():
                lab_item = {
                    "code": i["code"],
                    "name": name,
                    "room": i["room"],
                    "day": map[this_day],
                    "slot": slot["index"]
                }
                labs.append(lab_item)
    with open(f"{db_folder}labs.json", "w") as f:
        f.write(json.dumps(labs))
    return day_timetable

def get_name(code: str):
    if code == "" or code == " ":
        return "Free"
    global course_names
    if course_names == []:
        if not os.path.exists(f"{db_folder}courses.json"):
            with open(f"{db_folder}courses.json", "w") as f:
                f.write("[]")
        with open (f"{db_folder}courses.json", "r") as f:
            course_names = json.load(f)
    for i in course_names:
        if i["code"] == code:
            name:str = i["name"]
            return name
    new_name = input(f"We dont know the name for this course -> {code}, please enter the name to enrich the database: ")
    course_names.append({"code": code
                        ,"name": new_name})
    with open(f"{db_folder}courses.json", "w") as f:
        f.write(json.dumps(course_names))
    return new_name

def add_name_to_timetable(day_timetable: list, this_day: str):
    for slot in day_timetable:
        for i in slot["items"]:
                i["name"] = get_name(i["code"])
                name: str = i["name"]
                if " LAB" in name.strip().upper() or " DRAWING" in name.strip().upper():
                    lab_name_set.add(name)
                    lab_name_map[name] = {
                        "code": i["code"],
                        "room": i["room"]
                    }
                    key = this_day + str(slot["index"])
                    if key in lab_slots_map:
                        continue
                    else:
                        lab_slots_map[key] = True
                        lab_slot_start = slot["time"].split(" - ")[0]
                        lab_slot_end = ""
                        if slot["time"] == "08:00 - 08:55":
                            lab_slot_end = "10:55"
                        elif slot["time"] == "09:00 - 09:55":
                            lab_slot_end = "11:55"
                        elif slot["time"] == "10:00 - 10:55":
                            lab_slot_end = "12:55"
                        elif slot["time"] == "02:00 - 02:55":
                            lab_slot_end = "04:55"
                        extended_key = this_day + str(slot["index"]) + str(slot["index"]+1) + str(slot["index"]+2)
                        lab_days_with_slots_map[extended_key] = {"day": this_day, "slots": lab_slot_start + " - " + lab_slot_end}
                        two_key = this_day + str(slot["index"]+1)
                        three_key = this_day + str(slot["index"]+2)
                        lab_slots_map[two_key] = False
                        lab_slots_map[three_key] = False
    return day_timetable

def clean_day_timetable(day_timetable: list):
    for slot in day_timetable:
        for i in range(len(slot["items"])):
            for j in range(i+1,len(slot["items"])):
                if i == j:
                    continue
                if slot["items"][i]["code"] == slot["items"][j]["code"]:
                    if slot["items"][i]["room"] == slot["items"][j]["room"]:
                        slot["items"].pop(j)
                        break
                    else:
                        slot["items"][i]["room"] += ", " + slot["items"][j]["room"]
                        slot["items"].pop(j)
                        break
    return day_timetable

def timetable_day(this_day: str, days: list):
    start, end = get_start_end_days(days, this_day)
    day_timetable = find_day_timetable(this_day, start, end, days)
    data = populate_timetable_with_time(day_timetable, this_day)
    return data

def print_timetable_day(this_day: str, days: list):
    data = timetable_day(this_day, days)
    data_str = f"="*48+f"{this_day}"+"="*48+"\n"
    for i in data:
        data_str += f"{i['time']}\n"
        for j in i["items"]:
            if j["code"] == "":
                data_str += "Free\n\n"
            elif j["room"] == "":
                data_str += f"{j['code']}\n\n"
            else:
                data_str += f"{j['code']} - {j['room']}\n\n"
    data_str += "="*99+"\n\n"
    return data_str

def print_timetable():
    with open(f"{db_folder}timetable.txt", "w") as f:
        f.write("")
    final_list = timetable()
    for i in final_list:
        with open(f"{db_folder}timetable.txt", "a") as f:
            f.write(i)
            f.write("\n")

def manage_lab_with_chosen_slot(lab_name: str, chosen_slot: str):
    day_map = {
        "Mon": 0,
        "Tue": 1,
        "Wed": 2,
        "Thu": 3,
        "Fri": 4
    }
    global lab_choices
    if lab_name in lab_choices:
        print("Lab already chosen, skipping this lab")
        return
    lab_choices[lab_name] = {
        "slot": chosen_slot,
        "day": day_map[chosen_slot[:3]],
        "start": chosen_slot[3],
        "end": chosen_slot[5]
    }
    return

def ask_for_lab_choices():
    if lab_name_set == set([]):
        return
    print("select the slots for each lab.....")
    chosen_slots = set([])
    for lab in lab_name_set:
        print(f"Select the slot for the {lab}")
        ctr = 1
        lab_choice_map = {}
        for key in lab_days_with_slots_map:
            if key in chosen_slots:
                continue
            lab_choice_map[ctr] = key
            print(f"{ctr}. {lab_days_with_slots_map[key]['day']} {lab_days_with_slots_map[key]['slots']}")
            ctr += 1
        choice = int(input("Enter your choice: "))
        chosen_slot = lab_choice_map[choice]
        if choice < 1 or choice > len(lab_days_with_slots_map):
            choice = print("Invalid choice, try again")
            if choice < 1 or choice > len(lab_days_with_slots_map):
                print("Invalid choice, skipping this lab")
                continue
        if chosen_slot in chosen_slots:
            print("Slot already chosen, skipping this lab")
            continue
        chosen_slots.add(chosen_slot)
        manage_lab_with_chosen_slot(lab, chosen_slot)

def clear_lab_slots_in_table(timetable: list):
    day_map = {
        "Mon": 0,
        "Tue": 1,
        "Wed": 2,
        "Thu": 3,
        "Fri": 4
    }
    for lab_slot in lab_days_with_slots_map.keys():
        day_index = day_map[lab_slot[:3]]
        slot_indices = [int(lab_slot[3]), int(lab_slot[4]), int(lab_slot[5])]
        for day in range(len(timetable)):
            if day == day_index:
                empty = {
                    "code": "",
                    "room": "",
                    "name": "Free"
                }
                for slot in slot_indices:
                    timetable[day][slot]["items"] = [empty]
    return timetable

def insert_lab_choices_into_timetable(timetable: list):
    for lab_name in lab_choices.keys():
        day = lab_choices[lab_name]["day"]
        start = int(lab_choices[lab_name]["start"])
        end = int(lab_choices[lab_name]["end"])
        code = lab_name_map[lab_name]["code"]
        room = lab_name_map[lab_name]["room"]
        for slot in range(start, end+1):
            lab_item = {
                "code": code,
                "room": room,
                "name": lab_name
            }
            timetable[day][slot]["items"] = [lab_item]
    return timetable

def save_lab_choices():
    global lab_choices
    with open(f"{db_folder}lab_choices.json", "w") as f:
        f.write(json.dumps(lab_choices))

def load_lab_choices():
    global lab_choices
    if not os.path.exists(f"{db_folder}lab_choices.json"):
        return
    # check if the file is empty
    if os.stat(f"{db_folder}lab_choices.json").st_size == 0:
        return
    with open(f"{db_folder}lab_choices.json", "r") as f:
        lab_choices = json.load(f)

def timetable():
    soup = bs(open(f"{db_folder}timetable.html"), 'html.parser')
    table = soup.find("table", {"border":"1","cellpadding":"0","cellspacing":"0"})
    days = table.find_all("tr")[1:]
    refer_days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    final_list = []
    for day in refer_days:
        tmp = timetable_day(day, days)
        final_list.append(tmp)
    load_lab_choices()
    if lab_choices == {}:
        ask_for_lab_choices()
    final_list = clear_lab_slots_in_table(final_list)
    final_list = insert_lab_choices_into_timetable(final_list)
    save_lab_choices()
    return final_list

def post_courses():
    global course_names
    if not os.path.exists(f"{db_folder}courses.json"):
        with open(f"{db_folder}courses.json", "w") as f:
            f.write("[]")
    with open(f"{db_folder}courses.json", "r") as f:
        course_names = json.load(f)
    r = requests.post("https://maxbrain.vercel.app/erp/api/v1/course", json={"courses": course_names})
    if r.status_code == 200:
        print("Courses posted successfully")
    else:
        print("Error in posting courses")

def get_courses():
    r = requests.get("https://maxbrain.vercel.app/erp/api/v1/course")
    if r.status_code == 200:
        saveable = []
        for i in r.json().get("courses"):
            saveable.append({"code": i["code"], "name": i["name"]})
        with open(f"{db_folder}courses.json", "w") as f:
            f.write(json.dumps(saveable))
        print("Courses received successfully")
    else:
        print("Error in getting courses")

def getTimeTable(session: requests.Session, erpcreds: dict, log: bool = False, useCache: bool = True):
    if not os.path.exists(lib_folder):
        os.makedirs(lib_folder)
    if not os.path.exists(db_folder):
        os.makedirs(db_folder)
    if erp.session_alive(session):
        if log:
            print("Session is alive")
    else:
        ssoToken = ""
        if os.path.exists(sessionFile):
            with open(sessionFile, "r") as f:
                ssoToken = f.read()
        if not useCache:
            ssoToken = ""
        erp.set_cookie(session, "ssoToken", ssoToken)
        if not erp.session_alive(session):
            headers = {
                'timeout': '20',
                'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/51.0.2704.79 Chrome/51.0.2704.79 Safari/537.36',
            }
            _,ssoToken,error = erp.login(log=log, headers=headers, session=session, erpcreds=erpcreds)
            if error:
                return error
            with open(sessionFile, "w") as f:
                f.write(ssoToken)
            if log:
                print("Session Restored")
    tt = get_timetable(session=session, log=log)
    with open(f"{db_folder}timetable.html", "w") as f:
        f.write(tt)
    if not os.path.exists(db_folder):
            os.makedirs(db_folder)
    if not os.path.exists(f"{db_folder}courses.json"):
            get_courses()
    final = timetable()
    str_final = str(final).replace("'", '"')
    with open(f"{db_folder}timetable.json", "w") as f:
        f.write(str_final)

if __name__ == "__main__":
    args = sys.argv
    command = args[1]
    clear_choices = args[2] if len(args) > 2 else 'N'
    clear_labs = args[3] if len(args) > 3 else 'N'
    clear_lab_choices = args[4] if len(args) > 4 else 'N'
    if command == "-tt" or command == "--timetable":
        if not os.path.exists(db_folder):
            os.makedirs(db_folder)
        if clear_choices.upper() == 'Y' or clear_choices.upper() == 'YES':
            if os.path.exists(f"{db_folder}choices.json"):
                os.remove(f"{db_folder}choices.json")
                print("Choices cleared")
        if clear_labs.upper() == 'Y' or clear_labs.upper() == 'YES':
            if os.path.exists(f"{db_folder}labs.json"):
                os.remove(f"{db_folder}labs.json")
                print("Labs cleared")
        if clear_lab_choices.upper() == 'Y' or clear_lab_choices.upper() == 'YES':
            if os.path.exists(f"{db_folder}lab_choices.json"):
                os.remove(f"{db_folder}lab_choices.json")
                print("Lab choices cleared")
        if not os.path.exists(f"{db_folder}courses.json"):
            get_courses()
        final = timetable()
        str_final = str(final).replace("'", '"')
        with open(f"{db_folder}timetable.json", "w") as f:
            f.write(str_final)
    elif command == "-sc" or command == "--save-courses":
        post_courses()
    elif command == "-gc" or command == "--get-courses":
        get_courses()