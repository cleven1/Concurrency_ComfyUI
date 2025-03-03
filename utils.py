import json

def find_image_value(data):
    """
    从 JSON 数据中查找第一个 `image` 键的值
    """
    if isinstance(data, dict):
        # 如果当前字典中有 `image` 键，直接返回其值
        if "image" in data:
            image = data.get('image')
            if isinstance(image, str):
                return image
        # 否则递归查找子节点
        for key, value in data.items():
            result = find_image_value(value)
            if result is not None:
                return result
    elif isinstance(data, list):
        # 如果是列表，遍历每个元素递归查找
        for item in data:
            result = find_image_value(item)
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
    
    image_value = find_image_value(json_data)
    
    if image_value is not None:
        print(f"Found image value: {image_value}")
    else:
        print("No 'image' key found in the JSON.")

if __name__ == "__main__":
    json_file = "/Users/clevenzhao/Downloads/放大2倍 workflow_api.json"  # 替换为你的 JSON 文件路径
    main(json_file)
