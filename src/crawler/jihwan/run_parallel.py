import multiprocessing
import subprocess
import os
from tqdm import tqdm
import time

def run_script(file_path, position):
    try:
        # subprocess.run(["python", "-u", "crawler_v5.py", file_path, str(position)], check=True)
        subprocess.run(["python", "-u", "crawler_product_info.py", file_path, str(position)], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error while processing {file_path}: {e}")

if __name__ == "__main__":
    num_processes = os.cpu_count()

    # subprocess.run(["python", "url_crawler.py"])
    file_list = [f"../../data/jihwan/url/{url}" for url in sorted(os.listdir("../../data/jihwan/url"))]

    processes = []
    with tqdm(total=len(file_list), desc="Overall Progress") as pbar:
        idx = 0
        positions = list(range(1, num_processes + 1))
        while idx < len(file_list) or processes:
            while len(processes) < num_processes and idx < len(file_list):
                file_path = file_list[idx]
                position = positions[len(processes)]
                p = multiprocessing.Process(target=run_script, args=(file_path, position))
                processes.append((p, position))
                p.start()
                idx += 1

            for p, position in processes.copy():
                if not p.is_alive():
                    p.join()
                    processes.remove((p, position))
                    pbar.update(1)
            time.sleep(0.1)
