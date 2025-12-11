# 定义文件路径
user_setup_path = "D:/Backup/Documents/maya/2022/scripts/userSetup.mel"
 
# 定义要搜索的字符串
strings_to_search = ["CeresProjectLocate", "quickopenprojectfileopen"]
 
# 读取userSetup.mel文件的内容到一个列表中
with open(user_setup_path, 'r', encoding='utf-8') as user_setup_file:
    user_setup_lines = user_setup_file.readlines()
 
# 过滤掉包含指定字符串的行，并准备写入的新内容
new_user_setup_lines = [line for line in user_setup_lines if not any(s in line for s in strings_to_search)]
 
# 将新的内容写回到userSetup.mel文件中，每行有效内容之间添加一个空行
with open(user_setup_path, 'w', encoding='utf-8') as user_setup_file:
    for i, line in enumerate(new_user_setup_lines):
        if  line == '\n':
            continue
        else :
            user_setup_file.write(line + '\n')
 
# 打印完成信息
print(f"清理完成！！！")