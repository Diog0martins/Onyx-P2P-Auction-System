""" def cmd_status():

    user = load_info()
    print("====== USER INFO ======")
    for k, v in user.items():
        print(f"{k.capitalize():>10}: {v}")
    print("=======================\n")

 """