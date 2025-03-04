import json
from typing import Dict, Any

# 存储 prompt_id 和其对应的端口和时间
CACHES: Dict[str, Dict[str, Any]] = {}

def find_value(data, value: str):
    """
    从 JSON 数据中查找第一个 `image` 键的值
    """
    if isinstance(data, dict):
        # 如果当前字典中有 `image` 键，直接返回其值
        if value in data:
            image = data.get(value)
            if isinstance(image, str):
                return image
        # 否则递归查找子节点
        for key, v in data.items():
            result = find_value(v, value)
            if result is not None:
                return result
    elif isinstance(data, list):
        # 如果是列表，遍历每个元素递归查找
        for item in data:
            result = find_value(item, value)
            if result is not None:
                return result
    # 如果没有找到，返回 None
    return None

def main(json_file):
    """
    主函数：读取 JSON 文件并查找 `image` 值
    """
    with open(json_file, "r") as file:
        json_data = json.load(file)
    
    image_value = find_value(json_data, 'filename')
    
    if image_value is not None:
        print(f"Found image value: {image_value}")
    else:
        print("No 'image' key found in the JSON.")

if __name__ == "__main__":
    json_file = "/Users/clevenzhao/Downloads/test.json"  # 替换为你的 JSON 文件路径
    main(json_file)
