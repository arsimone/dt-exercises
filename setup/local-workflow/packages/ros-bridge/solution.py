#!/usr/bin/env python2
from __future__ import unicode_literals
from PIL import Image
import io

import os
import time
import sys

import argparse
import numpy as np
import roslaunch
from rosagent import ROSAgent

from aido_schemas import (protocol_agent_duckiebot1,EpisodeStart,Duckiebot1Observations, Context, GetCommands, Duckiebot1Commands, RGB, PWMCommands, LEDSCommands)
from zuper_nodes_wrapper import Context, wrap_direct, logger


class ROSBaselineAgent(object):
    def __init__(self, in_sim, launch_file):
        # Now, initialize the ROS stuff here:

        vehicle_name = os.getenv('VEHICLE_NAME')

        # The in_sim switch is used for local development
        # in that case, we do not start a launch file
        if not in_sim:
            # logger.info('Configuring logging')
            uuid = roslaunch.rlutil.get_or_generate_uuid(None, False)
            # roslaunch.configure_logging(uuid)
            # print('configured logging 2')
            roslaunch_path = os.path.join(os.getcwd(), launch_file)
            logger.info('Creating ROSLaunchParent')
            self.launch = roslaunch.parent.ROSLaunchParent(uuid, [roslaunch_path])

            logger.info('about to call start()')

            self.launch.start()
            logger.info('returning from start()')

        # Start the ROSAgent, which handles publishing images and subscribing to action
        logger.info('starting ROSAgent()')
        self.agent = ROSAgent()
        logger.info('started ROSAgent()')

        logger.info('completed __init__()')

    def on_received_seed(self, context: Context, data: int):
        logger.info('Received seed from pipes')
        np.random.seed(data)

    def on_received_episode_start(self, context: Context, data: EpisodeStart):
        logger.info("Starting episode")
        context.info('Starting episode %s.' % data)

    def on_received_observations(self, context: Context, data: Duckiebot1Observations):
        logger.info("received observation")
        sys.stdout.flush()
        jpg_data = data.camera.jpg_data
        obs = jpg2rgb(jpg_data)
        self.agent._publish_img(obs)
        self.agent._publish_info()

    def on_received_get_commands(self, context: Context, data: GetCommands):
        logger.info("Agent received GetCommand request")
        while not self.agent.updated:
            time.sleep(0.01)

        pwm_left, pwm_right = self.agent.action
        if self.agent.started:  # before starting, we send empty commnands to keep connection
            self.agent.updated = False

        grey = RGB(0.5, 0.5, 0.5)
        led_commands = LEDSCommands(grey, grey, grey, grey, grey)
        pwm_commands = PWMCommands(motor_left=pwm_left, motor_right=pwm_right)
        commands = Duckiebot1Commands(pwm_commands, led_commands)
        context.write('commands', commands)
        # logger.info("Agent send command:" + str(commands["wheels"]["motor_left"]))
        #print("Send command: " +str(commands["wheels"]["motor_left"]))
        #sys.stdout.flush()

    def finish(self, context: Context):
        context.info('finish()')


def jpg2rgb(image_data):
    """ Reads JPG bytes as RGB"""
    im = Image.open(io.BytesIO(image_data))
    im = im.convert('RGB')
    data = np.array(im)
    assert data.ndim == 3
    assert data.dtype == np.uint8
    return data


if __name__ == '__main__':

    # The following can be set in the environment file
    LOGLEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
    logger.setLevel(LOGLEVEL)
    logger.warn("Logger set to level: "+str(logger.level))
    if logger.level > 20:
        logger.warn("Logging is set to {}, info msg will no be shown".format(LOGLEVEL))
    logger.info("Started solution2.py")

    # parser = argparse.ArgumentParser()
    # parser.add_argument("-s","--sim", action="store_true", help="Add this option to start the car interface")
    # parser.add_argument("--launch_file",default="lf_slim.launch", help="launch file that should be used (default: lf_slim.launch")
    # args = parser.parse_args()
    # agent = ROSBaselineAgent(in_sim=args.sim, launch_file = args.launch_file)
    agent = ROSBaselineAgent(in_sim=True, launch_file = None)
    logger.info("Created agent in solution main")
    print("Started solution")
    sys.stdout.flush()
    wrap_direct(agent, protocol_agent_duckiebot1)
