
import concurrent.futures
import queue
import threading
from tkinter import *
from tkinter import filedialog, ttk
from tkinter.messagebox import showerror

import requests
from bs4 import BeautifulSoup


class WebCrawler:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("web crawler")
        self.root.geometry("600x400")

        self.urls = list()
        self.links = []
        self.count = 0
        self.number = 1
        self.threads = []
        self.lock = threading.Lock()
        self.queue = queue.Queue()
        self.stop = False
        self.save_path = ""
        
        self.threads_count = ttk.Entry()
        self.threads_count.grid(column=0, row=5, sticky=NSEW, padx=10)
        label = ttk.Label(text="Threads")
        label.grid(column=0, sticky=NS, row=4)

        links_in = ttk.Label(text="Links found that is already in db: 0")
        links_in.grid(column=1, sticky=NS, row=4)

        links_not_in = ttk.Label(text="Links found that is not in db: 0")
        links_not_in.grid(column=1, sticky=NS, row=5)

        domains_in = ttk.Label(text="Domains found that is already in db: 0")
        domains_in.grid(column=2, sticky=NS, row=4)

        domains_not_in = ttk.Label(text="Domains found that is not in db: 0")
        domains_not_in.grid(column=2, sticky=NS, row=5)

        # creating table
        columns = ("No", "url")

        self.tree = ttk.Treeview(columns=columns, show="headings")
        self.tree.grid(column=0, columnspan=3, row=0)

        self.tree.heading("No", text="No")
        self.tree.column("#1", width=60)
        self.tree.heading("url", text="url")
        self.tree.column("#2", width=500)

        # open button settings
        open_button = ttk.Button(text="Open file", command=self.load_file)
        open_button.grid(column=0, row=2, sticky=NSEW, padx=10)
        self.open_path = ttk.Entry()
        self.open_path.grid(column=1, row=2, columnspan=2, sticky=NSEW, padx=10)

        # save button settings
        save_button = ttk.Button(text="Save file", command=self.save_file)
        save_button.grid(column=0, row=3, sticky=NSEW, padx=10)
        self.save_path_entry = ttk.Entry()
        self.save_path_entry.grid(column=1, row=3, columnspan=2, sticky=NSEW, padx=10)

        # Create a vertical scrollbar and associate it with the treeview
        self.scrollbar = ttk.Scrollbar(
            self.root, orient=VERTICAL, command=self.tree.yview
        )
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        self.scrollbar.grid(column=3, row=0, rowspan=1, sticky=NS)

        # stop button settings
        self.stop_button = ttk.Button(text="Stop", command=self.stop_crawling, state="disabled")
        self.stop_button.grid(column=1, row=1, sticky=NSEW, padx=10)

        # how many grabbed in last hour

        self.grabbed = ttk.Label(text="Grabbed in last hour:")
        self.grabbed.grid(column=0, sticky=NS, row=6)

        self.button_crawl = ttk.Button(text="Start", command=self.start_crawling)
        self.button_crawl.grid(column=0, row=1, sticky=NSEW, padx=10)

        self.update_counter()
        self.update_treeview()
        self.reset_counter()
        self.crawl_thread = None
        self.root.mainloop()

    def start_crawling(self):
        
        if self.stop:
            self.stop = False
        self.stop_button["state"]="normal"
        self.button_crawl["state"]="disabled"
        self.crawl_thread = threading.Thread(target=self.crawl_web, daemon=True)
        self.crawl_thread.start()
        self.root.protocol("WM_DELETE_WINDOW", self.close_window)
        

    def stop_crawling(self):
        self.stop = True
        self.button_crawl["state"]="normal"
        self.stop_button["state"]="disabled"
        self.crawl_thread.join()

    def close_window(self):
        self.stop = True
        self.root.quit()
        self.root.destroy()
        # self.crawl_thread.join()
        

    # Function for loading the file from file explorer window
    def load_file(self):
        filepath = filedialog.askopenfilename()
        if filepath != "":
            self.open_path.delete(0, last=END)
            self.open_path.insert(0, filepath)
            with open(filepath, "r", encoding="UTF-8") as file:
                self.urls.clear()
                self.urls.extend(file.read().split("\n"))

    # Function for save the file
    def save_file(self):
        filepath = filedialog.asksaveasfilename()
        if filepath != "":
            self.save_path_entry.delete(0, last=END)
            self.save_path_entry.insert(0, filepath)
            self.save_path = filepath
            with open(filepath, "w", encoding="UTF-8") as file:
                for url in self.links:
                    file.write(url + "\n")

    def crawl_web(self):
        if len(self.links) != 0:
            self.links.clear()
        max_threads = 1
        try:
            max_threads = int(self.threads_count.get())
        except:
            showerror("Error", "Not valid threads count")
            return
        links = []
        temp = []
        for url in self.urls:
            temp.append(url)
            if len(temp) > len(self.urls) / max_threads:
                links.append(list(temp))
                temp.clear()

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_threads) as executor:
            futures = {executor.submit(self.extract_links, urls) for urls in links}

            for future in concurrent.futures.as_completed(futures):
                if self.stop:
                    executor.shutdown(wait=False)
                    return
                else:
                    future.result()
        

    def update_counter(self):
        value = "Grabbed in last hour: " + str(self.count)
        self.grabbed["text"] = str(value)
        if self.stop:
            return
        self.grabbed.after(1000, self.update_counter)

    def reset_counter(self):
        self.count = 0
        value = "Grabbed in last hour: " + str(self.count)
        self.grabbed["text"] = str(value)
        if self.stop:
            return
        self.grabbed.after(3600000,self.update_counter)

        

    def extract_links(self, urls):
        for url in urls:
            if self.stop:
                return
            try:
                response = requests.get(url, timeout=(3.05, 27))
                if response.status_code == 200:
                    soup = BeautifulSoup(
                        response.content, "html.parser", from_encoding="iso-8859-1"
                    )
                    all_links = [a["href"] for a in soup.find_all("a", href=True)]
                    for link in all_links:
                        if "http" in link:
                            self.links.append(link)
                            self.queue.put(link)
                            self.count += 1
            except requests.RequestException as e:
                # print("Error", f"An error occurred: {e}")
                pass

    def update_treeview(self):
        if self.stop:
            while not self.queue.empty():
                link = self.queue.get()
                self.tree.insert("", END, values=(self.number, link))
                self.number += 1
            return
        for _ in range(100):  # process up to 100 links at a time
            if not self.queue.empty():
                link = self.queue.get()
                self.tree.insert("", END, values=(self.number, link))
                self.number += 1
        # call this method again after 10000ms
        self.tree.after(5000, self.update_treeview)


crawler = WebCrawler()
