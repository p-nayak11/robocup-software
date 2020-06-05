#pragma once

#include <rclcpp/rclcpp.hpp>
#include <rj_robocup/msg/game_settings.hpp>
#include <rj_robocup/srv/set_game_settings.hpp>

namespace config_server {
using GameSettingsMsg = rj_robocup::msg::GameSettings;
using SetGameSettingsSrv = rj_robocup::srv::SetGameSettings;

class ConfigServer : public rclcpp::Node {
public:
    ConfigServer(rclcpp::NodeOptions node_options);

private:
    void setGameSettingsCallback(const GameSettingsMsg& game_settings);
    void broadcastGameSettings();

    GameSettingsMsg game_settings_;
    rclcpp::Service<SetGameSettingsSrv>::SharedPtr server_;
    rclcpp::Publisher<GameSettingsMsg>::SharedPtr publisher_;
};
}  // namespace config_server
