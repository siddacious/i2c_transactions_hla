def get_shift(mask):
    for i in range(7, -1, -1):
        if mask > (1<<i):
            continue
        return i
    return None

if __name__ == "__main__":

    for i in range(7, -1, -1):
        print(i)
        msk = (1<<i)-1
        print("Mask:", format(msk, "#010b"), get_shift(msk))
        msk = (1<<i)
        print("Mask:", format(msk, "#010b"), get_shift(msk))
        shft= (8-i)
        msk = (1<<i)-1 << shft
        print("Mask:", format(msk, "#010b"),"shft", shft,  get_shift(msk))
        print()