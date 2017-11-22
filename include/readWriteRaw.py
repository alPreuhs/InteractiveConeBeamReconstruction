import numpy as np

"""

"""


def read(filename):
    """
    :param filename: name of raw data file that is ordered as follows:
    3 number in int16 format (2bytes each number -> 6byte header) encoding the height,width and number of matrices,
    followed by the matrix indices in float64 (6 byte) format.
    :return:
    List of matrices
    """
    file = open(filename, 'r')
    proj_dim = np.memmap(file, dtype=np.uint16, mode='r', offset=0, shape=3)
    proj_buff = np.memmap(file, dtype=np.float64, mode='r', offset=6, shape=proj_dim[0] * proj_dim[1] * proj_dim[2])

    proj_len = proj_dim[0] * proj_dim[1]
    p_list = []
    print()
    print()
    print()
    print(proj_dim[1])
    print(proj_dim[2])
    for i in range(0, proj_dim[2]):
        p_list.append(np.array(proj_buff[i * proj_len: (i + 1) * proj_len]).reshape(proj_dim[1], proj_dim[0], order='F'))
        # p_list.append(np.array(proj_buff[i * proj_len: (i + 1) * proj_len]).reshape(3, 4))

    return p_list


"""
expects a filename as a string and the projection matrices as a list, whereas each projection matrix is a np.array
"""


def write(filename, p_Mat):
    # generate header
    p_len = len(p_Mat)
    p_height = p_Mat[0].shape[0]
    p_width = p_Mat[0].shape[1]
    header = bytearray(np.array([p_width, p_height, p_len]).astype('uint16'))
    # generate array
    transposed_p_Mat = []
    for p in p_Mat:
        transposed_p_Mat.append(p.transpose())

    body = bytearray(np.asarray(transposed_p_Mat).flatten().astype('float64'))

    f = open(filename, "wb")
    f.write(header)
    f.write(body)
    f.close()
