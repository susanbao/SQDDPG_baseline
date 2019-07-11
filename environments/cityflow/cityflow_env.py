#!/usr/bin/env python
# -*- coding: utf-8 -*-
# origin from https://github.com/IC3Net/IC3Net/blob/master/ic3net-envs/ic3net_envs/predator_prey_env.py
# edit by YuanZhang (2019.03.27)

# core modules
import random
import math

# 3rd party modules
import gym
import numpy as np
from gym import spaces

import cityflow
import pandas as pd
import os
import json


class CityFlowEnv(gym.Env):
    # metadata = {'render.modes': ['human']}

    def __init__(self,):

        self.episode_over = False
        self.coef = 0.1
        
        # easy version
        config_path = '/home/CityFlow/conf/.json'
        roadnet_path = ''
        
        self.engine = cityflow.Engine(config_path)
        self.lane_phase_info_dict = parse_roadnet(roadnet_path)

        self.intersection_list = self.lane_phase_info_dict.keys()
        self.n = len(self.intersection_list) # number of intersections
        self.naction = len(self.lane_phase_info_dict[self.intersection_list[0]]["phase"])
        self.obs_dim = len(self.lane_phase_info_dict[self.intersection_list[0]]['start_lane']) + 1
        
        # initialize previous action
        self.current_phase = {intersection_id:0  for intersection_id in self.intersection_list}
        
        # gym like environment
        self.action_space = []
        self.observation_space = []
        for agent_id in range(self.n):
            self.action_space.append(spaces.Discrete(self.naction))
            self.observation_space.append(spaces.Box)
        return


    def step(self, actions):

        for i, action in enumerate(actions):
            intersection_id = self.intersection_list[i]
            phase_id = np.argmax(action)
            # take action 
            self.eng.set_tl_phase(ntersection_id, phase_id)
            self.current_phase[intersection_id] = phase_id

        self.eng.next_step()
        
        debug = {}
        return self._get_obs(),  self._get_reward(), self.episode_over, debug
        
        
    def reset(self):
        self.eng.reset()
        return self._get_obs()
        
    def _get_obs(self):
        
#         state = {}
#         state['lane_vehicle_count'] = self.eng.get_lane_vehicle_count()  # {lane_id: lane_count, ...}
#         state['lane_waiting_vehicle_count'] = self.eng.get_lane_waiting_vehicle_count()  # {lane_id: lane_waiting_count, ...}
#         state['lane_vehicles'] = self.eng.get_lane_vehicles()  # {lane_id: [vehicle1_id, vehicle2_id, ...], ...}
#         state['vehicle_speed'] = self.eng.get_vehicle_speed()  # {vehicle_id: vehicle_speed, ...}
#         state['vehicle_distance'] = self.eng.get_vehicle_distance() # {vehicle_id: distance, ...}
        
        observations = []
        for intersection_id in self.intersection_list:     
            start_lane = self.lane_phase_info_dict[intersection_id]['start_lane']
            state = {}
            state['current_phase'] = self.current_phase[intersection_id]
            state['start_lane_vehicle_count'] = {lane: self.eng.get_lane_vehicle_count()[lane] for lane in start_lane}
            observations.append(np.array(list(state['start_lane_vehicle_count'].values()) + [state['current_phase']]))
                            
        return observations


    def _get_reward(self):
        mean_speed = np.mean(self.eng.get_vehicle_speed().values())                                        
        mean_reward = mean_speed * self.coef                                                                          
        return [mean_reward] * self.n                                          

                                                        
def parse_roadnet(roadnetFile):
                                                        
    roadnet = json.load(open(roadnetFile))
    lane_phase_info_dict ={}
                                                        
    # many intersections exist in the roadnet and virtual intersection is controlled by signal
    for intersection in roadnet["intersections"]:
        if intersection['virtual']:
            continue
                                                        
        lane_phase_info_dict[intersection['id']] = {"start_lane": [],
                                                     "end_lane": [],
                                                     "phase": [],
                                                     "phase_startLane_mapping": {},
                                                     "phase_roadLink_mapping": {}}
                                                                 
        road_links = intersection["roadLinks"]

        start_lane = []
        end_lane = []
        roadLink_lane_pair = {ri: [] for ri in range(len(road_links))}  # roadLink includes some lane_pair: (start_lane, end_lane)

        for ri in range(len(road_links)):
            road_link = road_links[ri]
            for lane_link in road_link["laneLinks"]:
                sl = road_link['startRoad'] + "_" + str(lane_link["startLaneIndex"])
                el = road_link['endRoad'] + "_" + str(lane_link["endLaneIndex"])
                start_lane.append(sl)
                end_lane.append(el)
                roadLink_lane_pair[ri].append((sl, el))

        lane_phase_info_dict[intersection['id']]["start_lane"] = sorted(list(set(start_lane)))
        lane_phase_info_dict[intersection['id']]["end_lane"] = sorted(list(set(end_lane)))

        for phase_i in range(len(intersection["trafficLight"]["lightphases"])):
            p = intersection["trafficLight"]["lightphases"][phase_i]
            lane_pair = []
            start_lane = []
            for ri in p["availableRoadLinks"]:
                lane_pair.extend(roadLink_lane_pair[ri])
                if roadLink_lane_pair[ri][0][0] not in start_lane:
                    start_lane.append(roadLink_lane_pair[ri][0][0])
            lane_phase_info_dict[intersection['id']]["phase"].append(phase_i)
            lane_phase_info_dict[intersection['id']]["phase_startLane_mapping"][phase_i] = start_lane
            lane_phase_info_dict[intersection['id']]["phase_roadLink_mapping"][phase_i] = lane_pair
    return lane_phase_info_dict