import multiprocessing as mp

from mlcourse_prac.check_process import check_process
from mlcourse_prac.submit_process import submit_process


def main():
    mp.Process(target=check_process).start()
    mp.Process(target=submit_process).start()


if __name__ == '__main__':
    main()
