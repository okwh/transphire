"""
    TranSPHIRE is supposed to help with the cryo-EM data collection
    Copyright (C) 2017 Markus Stabrin

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os


def get_motion_default(settings, motion_frames, queue_com, name):
    """
    Set the default values for the motion correction software.

    settings - TranSPHIRE settings.
    motion_frames - Sub frame settings.
    queue_com - Queue for communication.
    name - Name of the process.

    Returns:
    True, if dose weighting will be applied.
    """

    motion_name = settings['Copy']['Motion']
    if motion_name == 'MotionCor2 v1.0.0' or \
            motion_name == 'MotionCor2 v1.0.5' or \
            motion_name == 'MotionCor2 v1.1.0':
        motion_frames['last'] = \
            int(settings['General']['Number of frames']) - \
            int(settings[motion_name]['-Trunc'])
        motion_frames['first'] = \
            int(settings[motion_name]['-Throw']) + 1

        return bool(
                settings[motion_name]['-FmDose'] != '0' and
                settings[motion_name]['-PixSize'] != '0' and
                settings[motion_name]['-kV'] != '0'
                )

    elif motion_name == 'Unblur v1.0.2':
        motion_frames['last'] = int(settings['General']['Number of frames'])
        motion_frames['first'] = 1

        return bool(settings[motion_name]['Apply Dose filter?'] == 'True')

    else:
        message = '\n'.join([
            '{0}: Motion version not known.'.format(motion_name),
            'Please contact the TranSPHIRE authors!'
            ])
        queue_com['error'].put(
            message,
            name
            )
        raise IOError(message)


def get_dw_file_name(output_transfer_scratch, file_name, settings, queue_com, name):
    """
    Get the name of the dose weighted file directly after the program finished.

    output_transfer - Name of the folder in the scratch directory.
    file_name - File name of the root_name path.
    settings - TranSPHIRE settings.
    queue_com - Queue for communication.
    name - Name of the process.

    Returns:
    File path of the DW file.
    """
    motion_name = settings['Copy']['Motion']
    if motion_name == 'MotionCor2 v1.0.0' or \
            motion_name == 'MotionCor2 v1.0.5' or \
            motion_name == 'MotionCor2 v1.1.0':
        return os.path.join(
            output_transfer_scratch,
            '{0}_DW.mrc'.format(file_name)
            )

    elif motion_name == 'Unblur v1.0.2':
        return os.path.join(
            output_transfer_scratch,
            '{0}_DW.mrc'.format(file_name)
            )

    else:
        message = '\n'.join([
            '{0}: Motion version not known.'.format(motion_name),
            'Please contact the TranSPHIRE authors!'
            ])
        queue_com['error'].put(
            message,
            name
            )
        raise IOError(message)


def get_motion_command(file_input, file_output_scratch, file_log_scratch, settings, queue_com, name, file_shift):
    """
    Get the command for the selected motion software.

    file_input - Input file for motion correction.
    file_output_scratch - Output file name
    file_log_scratch - Logfile path on the scratch disc
    settings - TranSPHIRE settings.
    queue_com - Queue for communication.
    name - Name of the process.
    file_shift - Path of file with zeros shift

    Returns:
    Motion command
    """
    motion_name = settings['Copy']['Motion']
    command = None
    block_gpu = None
    gpu_list = None
    shell = None
    if motion_name == 'MotionCor2 v1.0.0' or \
            motion_name == 'MotionCor2 v1.0.5' or \
            motion_name == 'MotionCor2 v1.1.0':
        command = create_motion_cor_2_v1_0_0_command(
            motion_name=motion_name,
            file_input=file_input,
            file_output=file_output_scratch,
            file_log=file_log_scratch,
            settings=settings,
            queue_com=queue_com,
            name=name
            )
        gpu_list = settings[motion_name]['-Gpu'].split()
        shell = False

        if motion_name == 'MotionCor2 v1.0.0':
            block_gpu = False
        elif motion_name == 'MotionCor2 v1.0.5':
            block_gpu = True
        elif motion_name == 'MotionCor2 v1.1.0':
            if settings[motion_name]['-GpuMemUsage'] == '0':
                block_gpu = False
            else:
                block_gpu = True

    elif motion_name == 'Unblur v1.0.2':
        command = create_unblur_v1_0_2_command(
            motion_name=settings['Copy']['Motion'],
            file_input=file_input,
            file_output=file_output_scratch,
            file_log=file_log_scratch,
            settings=settings,
            queue_com=queue_com,
            name=name
            )
        gpu_list = []
        block_gpu = False
        shell = True

    else:
        message = '\n'.join([
            '{0}: Motion version not known.'.format(settings['Copy']['Motion']),
            'Please contact the TranSPHIRE authors!'
            ])
        queue_com['error'].put(
            message,
            name
            )
        raise IOError(message)

    assert command is not None, 'command not specified: {0}'.format(motion_name)
    assert block_gpu is not None, 'block_gpu not specified: {0}'.format(motion_name)
    assert gpu_list is not None, 'gpu_list not specified: {0}'.format(motion_name)

    return command, block_gpu, gpu_list, shell


def create_motion_cor_2_v1_0_0_command(motion_name, file_input, file_output, file_log, settings, queue_com, name):
    """
    Create the MotionCor2 v1.0.0 command

    file_input - Input file for motion correction.
    file_output - Output filename
    file_log - Logfile name
    settings - TranSPHIRE settings.
    queue_com - Queue for communication.
    name - Name of the process.

    Returns:
    Command for MotionCor2 v1.0.0
    """

    command = []
    # Start the program
    command.append('{0}'.format(settings['Path'][motion_name]))
    # Input Micrograph
    _, extension = os.path.splitext(file_input)
    if extension == '.tiff' or \
            extension == '.tif':
        command.append('-InTiff')
        command.append('{0}'.format(file_input))

    elif extension == '.mrc':
        command.append('-InMrc')
        command.append('{0}'.format(file_input))

    else:
        message = '{0}: Not known!'.format(extension)
        queue_com['error'].put(message, name)
        raise IOError(message)

    # Output micrograph
    command.append('-OutMrc')
    command.append('{0}'.format(file_output))
    # Write the output stack
    command.append('-OutStack')
    command.append('1')
    # Log file
    command.append('-LogFile')
    command.append('{0}'.format(file_log))

    for key in settings[motion_name]:
        if settings[motion_name][key]:
            command.append(key)
            command.append(
                '{0}'.format(settings[motion_name][key])
                )
        else:
            continue

    return ' '.join(command)


def create_sum_movie_command(
        motion_frames, file_input, file_output, file_shift, file_frc,
        settings, queue_com, name
        ):
    """
    Create the SumMovie command.

    motion_frames - Sub frames settings dictionary
    file_input - File to sum.
    file_output - Output file name
    file_shift - Output shift file name
    file_frc - Output frc file name
    settings - TranSPHIRE settings
    queue_com - Queue for communication
    name - Name of the process

    Returns:
    Command for SumMovie
    """
    command = create_sum_movie_v1_0_2_command(
        file_input=file_input,
        file_output=file_output,
        file_shift=file_shift,
        file_frc=file_frc,
        first=motion_frames['first'],
        last=motion_frames['last'],
        settings=settings,
        queue_com=queue_com,
        name=name
        )
    block_gpu = False
    gpu_list = []
    return command, block_gpu, gpu_list


def create_unblur_v1_0_2_command(
        motion_name, file_input, file_output, file_log,
        settings, queue_com, name
        ):
    """
    Create the Unblur v1.0.2 command.

    motion_name - Sub frames settings dictionary
    file_input - File to sum.
    file_output - Output file name
    file_shift - Output shift file name
    settings - TranSPHIRE settings
    queue_com - Queue for communication
    name - Name of the process

    Returns:
    Command for Unblur v1.0.2
    """
    file_shift = '{0}_shift.txt'.format(file_log)
    file_frc = '{0}_frc.txt'.format(file_log)
    file_stack = '{0}_Stk.mrc'.format(os.path.splitext(file_output)[0])
    unblur_command = []
    # Input file
    unblur_command.append('{0}'.format(file_input))
    # Number of frames
    unblur_command.append('{0}'.format(settings['General']['Number of frames']))
    # Output sum file
    unblur_command.append('{0}'.format(file_output))
    # Output shift file
    unblur_command.append('{0}'.format(file_shift))
    # Pixel size
    unblur_command.append('{0}'.format(settings[motion_name]['Pixel size of images (A)']))
    # Dose weighting
    if settings[motion_name]['Apply Dose filter?'] == 'True':
        unblur_command.append('{0}'.format('Yes'))
        unblur_command.append('{0}'.format(settings[motion_name]['Exposure per frame (e/A^2)']))
        unblur_command.append('{0}'.format(settings[motion_name]['Acceleration voltage (kV)']))
        unblur_command.append('{0}'.format(settings[motion_name]['Pre-exposure amount(e/A^2)']))
    else:
        unblur_command.append('{0}'.format('No'))
    # Save aligned frames
    unblur_command.append('{0}'.format('Yes'))
    unblur_command.append('{0}'.format(file_stack))
    if settings[motion_name]['Set Expert Options?'] == 'True':
        unblur_command.append('{0}'.format(file_frc))
        unblur_command.append('{0}'.format(settings[motion_name]['Minimum shift for initial search (Angstroms)']))
        unblur_command.append('{0}'.format(settings[motion_name]['Outer radius shift limit (Angstroms)']))
        unblur_command.append('{0}'.format(settings[motion_name]['B-factor to apply to images (A^2)']))
        unblur_command.append('{0}'.format(settings[motion_name]['Half-width of central vertical line of Fourier mask']))
        unblur_command.append('{0}'.format(settings[motion_name]['Half-width of central horizontal line of Fourier mask']))
        unblur_command.append('{0}'.format(settings[motion_name]['Termination shift threshold']))
        unblur_command.append('{0}'.format(settings[motion_name]['Maximum number of iterations']))
        if settings[motion_name]['Restore Noise Power'] == 'True':
            unblur_command.append('{0}'.format('Yes'))
        else:
            unblur_command.append('{0}'.format('No'))
        if settings[motion_name]['Verbose Output?'] == 'True':
            unblur_command.append('{0}'.format('Yes'))
        else:
            unblur_command.append('{0}'.format('No'))
    else:
        unblur_command.append('{0}'.format('No'))

    command = []
    command.append(
        'echo "{0}" | {1}'.format(
            '\n'.join(unblur_command),
            '{0}'.format(settings['Path']['Unblur v1.0.2'])
            )
        )
    command.append(';')
    command.append(
        create_sum_movie_v1_0_2_command(
            file_input=file_input,
            file_output=file_output,
            file_shift=file_shift,
            file_frc=file_frc,
            first=int(settings[motion_name]['Throw'])+1,
            last=\
                int(settings['General']['Number of frames'])-\
                int(settings[motion_name]['Trunc']),
            settings=settings,
            queue_com=queue_com,
            name=name
            )
        )

    return ' '.join(command)


def create_sum_movie_v1_0_2_command(
        file_input, file_output, file_shift, file_frc,
        settings, queue_com, name, first, last
        ):
    """
    Create the SumMovie v1.0.2 command.

    file_input - File to sum.
    file_output - Output file name
    file_shift - Output shift file name
    file_frc - Output frc file name
    settings - TranSPHIRE settings
    queue_com - Queue for communication
    name - Name of the process

    Returns:
    Command for Summovie v1.0.2
    """
    sum_movie_command = []
    # Input file
    sum_movie_command.append('{0}'.format(file_input))
    # Number of frames

    motion_name = settings['Copy']['Motion']
    if motion_name == 'MotionCor2 v1.0.0' or \
            motion_name == 'MotionCor2 v1.0.5' or \
            motion_name == 'MotionCor2 v1.1.0':
        sum_movie_command.append('{0}'.format(
            int(settings['General']['Number of frames']) -
            int(settings[motion_name]['-Trunc']) -
            int(settings[motion_name]['-Throw'])
            ))

    elif motion_name == 'Unblur v1.0.2':
        sum_movie_command.append('{0}'.format(settings['General']['Number of frames']))

    else:
        message = '\n'.join([
            '{0}: Motion version not known.'.format(motion_name),
            'Please contact the TranSPHIRE authors!'
            ])
        queue_com['error'].put(
            message,
            name
            )
        raise IOError(message)

    # Output sum file
    sum_movie_command.append('{0}'.format(file_output))
    # Shift file
    sum_movie_command.append('{0}'.format(file_shift))
    # FRC file
    sum_movie_command.append('{0}'.format(file_frc))
    # First frame
    sum_movie_command.append('{0}'.format(first))
    # Last frame
    sum_movie_command.append('{0}'.format(last))
    # Pixel size

    if motion_name == 'MotionCor2 v1.0.0' or \
            motion_name == 'MotionCor2 v1.0.5' or \
            motion_name == 'MotionCor2 v1.1.0':
        sum_movie_command.append(
            '{0}'.format(settings[motion_name]['-PixSize'])
            )

    elif motion_name == 'Unblur v1.0.2':
        sum_movie_command.append(
            '{0}'.format(settings[motion_name]['Pixel size of images (A)'])
            )

    else:
        message = '\n'.join([
            '{0}: Motion version not known.'.format(motion_name),
            'Please contact the TranSPHIRE authors!'
            ])
        queue_com['error'].put(
            message,
            name
            )
        raise IOError(message)

    # Dose correction
    if motion_name == 'Unblur v1.0.2':
        if settings[motion_name]['Apply Dose filter?'] == 'True':
            sum_movie_command.append('{0}'.format('Yes'))
            sum_movie_command.append('{0}'.format(settings[motion_name]['Exposure per frame (e/A^2)']))
            sum_movie_command.append('{0}'.format(settings[motion_name]['Acceleration voltage (kV)']))
            sum_movie_command.append('{0}'.format(settings[motion_name]['Pre-exposure amount(e/A^2)']))
        else:
            unblur_command.append('{0}'.format('No'))
    else:
        sum_movie_command.append('No')

    command = 'echo "{0}" | {1}'.format(
        '\n'.join(sum_movie_command),
        '{0}'.format(settings['Path']['SumMovie v1.0.2'])
        )

    return command
