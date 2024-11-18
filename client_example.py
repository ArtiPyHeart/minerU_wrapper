import requests


def convert_pdf_to_markdown(pdf_path: str) -> str:
    """
    调用本地Flask服务将PDF转换为Markdown文本

    Args:
        pdf_path: PDF文件的路径或URL

    Returns:
        str: Markdown格式的文本内容

    Raises:
        Exception: 当服务调用失败时抛出异常
    """
    response = requests.post(
        "http://127.0.0.1:9999/convert", json={"path": pdf_path}
    )

    if response.status_code != 200:
        raise Exception(f"转换失败: {response.json().get('error', '未知错误')}")

    return response.json()["markdown"]


if __name__ == "__main__":
    # 使用示例
    markdown_content = convert_pdf_to_markdown(
        "https://kfqgw.beijing.gov.cn/zwgkkfq/2024zcwj/202411/W020241106391243575876.docx"
        # 替换为实际的PDF路径
    )
    print(markdown_content)
