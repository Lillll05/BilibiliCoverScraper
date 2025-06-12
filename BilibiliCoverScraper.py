import requests
import os
import re
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import threading
from concurrent.futures import ThreadPoolExecutor
import time

class BilibiliCoverScraper:
    def __init__(self, root):
        """
        初始化爬虫工具界面和基本变量
        """
        self.root = root
        self.root.title("B站作品封面爬取工具")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # 初始化变量
        self.current_page = 1
        self.total_pages = 2
        self.save_path = os.getcwd() + "/bilibili_covers"
        self.downloaded_count = 0
        self.total_items = 0
        self.is_running = False
        self.executor = None
        
        # 创建网络请求会话（复用TCP连接）
        self.session = requests.Session()
        
        # 创建界面
        self.create_widgets()
    
    def create_widgets(self):
        """
        创建GUI界面组件
        """
        # 顶部框架 - 页数设置
        page_frame = tk.Frame(self.root)
        page_frame.pack(padx=10, pady=10, fill=tk.X)
        
        tk.Label(page_frame, text="起始页:").pack(side=tk.LEFT)
        self.start_page = tk.Entry(page_frame, width=5)
        self.start_page.pack(side=tk.LEFT, padx=5)
        self.start_page.insert(0, "1")
        
        tk.Label(page_frame, text="结束页:").pack(side=tk.LEFT, padx=10)
        self.end_page = tk.Entry(page_frame, width=5)
        self.end_page.pack(side=tk.LEFT, padx=5)
        self.end_page.insert(0, "2")
        
        # 路径选择框架
        path_frame = tk.Frame(self.root)
        path_frame.pack(padx=10, pady=10, fill=tk.X)
        
        tk.Label(path_frame, text="保存路径:").pack(side=tk.LEFT)
        self.path_entry = tk.Entry(path_frame, width=40)
        self.path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.path_entry.insert(0, self.save_path)
        
        tk.Button(path_frame, text="浏览", command=self.select_save_path).pack(side=tk.LEFT, padx=5)
        
        # 进度条
        progress_frame = tk.Frame(self.root)
        progress_frame.pack(padx=10, pady=10, fill=tk.X)
        
        tk.Label(progress_frame, text="下载进度:").pack(side=tk.LEFT)
        self.progress_bar = ttk.Progressbar(progress_frame, length=400, mode="determinate")
        self.progress_bar.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.status_label = tk.Label(progress_frame, text="就绪")
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # 控制按钮
        button_frame = tk.Frame(self.root)
        button_frame.pack(padx=10, pady=10)
        
        self.start_button = tk.Button(button_frame, text="开始爬取", command=self.start_crawling)
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(button_frame, text="停止爬取", command=self.stop_crawling, state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        # 日志显示
        log_frame = tk.Frame(self.root)
        log_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        
        tk.Label(log_frame, text="下载日志:").pack(anchor=tk.W)
        self.log_text = tk.Text(log_frame, height=15, width=70)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        scrollbar = tk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.log_text.yview)
    
    def select_save_path(self):
        """
        选择保存封面图片的目录
        """
        folder = filedialog.askdirectory()
        if folder:
            self.save_path = folder
            self.path_entry.delete(0, tk.END)
            self.path_entry.insert(0, self.save_path)
    
    def log(self, message):
        """
        向日志文本框添加消息
        """
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
    
    def validate_title(self, title):
        """
        处理文件名中的非法字符
        """
        pattern = r"[\\\/\:\*\?\"\<\>\|]"
        new_title = re.sub(pattern, '_', title)
        return new_title
    
    def download_image(self, title, cover_url):
        """
        下载并保存封面图片
        """
        if not self.is_running:
            return
        
        try:
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
            }
            response = self.session.get(cover_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # 处理文件名
                safe_title = self.validate_title(title)
                file_path = os.path.join(self.save_path, f"{safe_title}.jpg")
                
                # 保存图片
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                # 更新进度
                self.downloaded_count += 1
                progress = (self.downloaded_count / self.total_items) * 100
                self.root.after(0, lambda: self.progress_bar.config(value=progress))
                self.root.after(0, lambda: self.status_label.config(text=f"已下载: {self.downloaded_count}/{self.total_items}"))
                self.root.after(0, lambda: self.log(f"成功下载: {title}.jpg"))
            else:
                self.root.after(0, lambda: self.log(f"下载失败: {title}, 状态码: {response.status_code}"))
        except Exception as e:
            self.root.after(0, lambda: self.log(f"下载出错: {title}, 错误: {str(e)}"))
    
    def get_page_data(self, page):
        """
        获取指定页面的动漫列表数据
        """
        if not self.is_running:
            return []
        
        try:
            url = f"https://api.bilibili.com/pgc/season/index/result?st=1&order=3&season_version=-1&spoken_language_type=-1&area=-1&is_finish=-1&copyright=-1&season_status=-1&season_month=-1&year=-1&style_id=-1&sort=0&page={page}&season_type=1&pagesize=20&type=1"
            headers = {
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36'
            }
            response = self.session.get(url, headers=headers, timeout=15)
            data = response.json()
            return data.get('data', {}).get('list', [])
        except Exception as e:
            self.root.after(0, lambda: self.log(f"获取页面 {page} 数据出错: {str(e)}"))
            return []
    
    def start_crawling(self):
        """
        开始爬取任务
        """
        if self.is_running:
            return
        
        # 清空日志
        self.log_text.delete(1.0, tk.END)
        
        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.status_label.config(text="爬取中...")
        
        # 在新线程中执行爬取任务
        threading.Thread(target=self.crawl_task, daemon=True).start()
    
    def stop_crawling(self):
        """
        停止爬取任务
        """
        self.is_running = False
        self.log("用户已停止爬取")
    
    def finish_crawling(self):
        """
        完成爬取后的清理工作
        """
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        if self.downloaded_count > 0:
            self.status_label.config(text=f"爬取完成，共下载 {self.downloaded_count} 个封面")
            self.log(f"===== 爬取完成，保存路径: {self.save_path} =====")
        else:
            self.status_label.config(text="爬取已停止，未下载任何封面")

    def crawl_task(self):
        """
        爬取任务主函数
        """
        try:
            # 创建保存目录
            if not os.path.exists(self.save_path):
                os.makedirs(self.save_path)
            
            start = int(self.start_page.get())
            end = int(self.end_page.get())
            
            if start < 1:
                start = 1
            if end < start:
                end = start
            
            self.total_pages = end
            self.current_page = start
            self.downloaded_count = 0
            self.total_items = 0
            
            # 计算总项目数
            for page in range(start, end + 1):
                items = self.get_page_data(page)
                self.total_items += len(items)
            
            if self.total_items == 0:
                self.root.after(0, lambda: messagebox.showwarning("警告", "未获取到任何数据，请检查网络或页数设置"))
                self.finish_crawling()
                return
            
            # 初始化进度条
            self.root.after(0, lambda: self.progress_bar.config(max=100, value=0))
            self.root.after(0, lambda: self.status_label.config(text=f"准备下载: {self.total_items} 个封面"))
            
            # 开始下载
            with ThreadPoolExecutor(max_workers=5) as executor:
                for page in range(start, end + 1):
                    if not self.is_running:
                        break
                    
                    self.root.after(0, lambda p=page: self.log(f"正在获取第 {p} 页数据..."))
                    items = self.get_page_data(page)
                    
                    for item in items:
                        if not self.is_running:
                            break
                        
                        title = item.get('title', '未知标题')
                        cover = item.get('cover', '')
                        
                        if title and cover:
                            executor.submit(self.download_image, title, cover)
                        else:
                            self.root.after(0, lambda t=title: self.log(f"跳过无效数据: {t}"))
                    
                    if not self.is_running:
                        break
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"爬取过程中出错: {str(e)}"))
        finally:
            self.finish_crawling()

if __name__ == "__main__":
    root = tk.Tk()
    app = BilibiliCoverScraper(root)
    root.mainloop()