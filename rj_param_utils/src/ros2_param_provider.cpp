#include <rj_param_utils/ros2_param_provider.hpp>
#include <spdlog/spdlog.h>

namespace params {

ROS2ParamProvider::ROS2ParamProvider(rclcpp::Node* node, const std::string& module)
    : ParamProvider{module} {
    DeclareParameters(node);
    //InitUpdateParamCallbacks(node);
}

rcl_interfaces::msg::SetParametersResult ROS2ParamProvider::UpdateParameters(const std::vector<rcl_interfaces::msg::Parameter_<std::allocator<void>>>& params) {
    using rcl_interfaces::msg::SetParametersResult;

    bool all_succeeded = true;
    for (const rcl_interfaces::msg::Parameter_<std::allocator<void>>& param : params) {
        std::string full_name = ConvertFullNameFromROS2(param.name);
        bool success = false;
        //success = this->TryUpdate(full_name, param.value);
        /*switch (param.type) {
            case rclcpp::PARAMETER_BOOL:
                success = TryUpdate(full_name, param.as_bool());
                break;
            case rclcpp::PARAMETER_INTEGER:
                success = TryUpdate(full_name, param.as_int());
                break;
            case rclcpp::PARAMETER_DOUBLE:
                success = TryUpdate(full_name, param.as_double());
                break;
            case rclcpp::PARAMETER_STRING:
                success = TryUpdate(full_name, param.as_string());
                break;
            case rclcpp::PARAMETER_BYTE_ARRAY:
                success = TryUpdate(full_name, param.as_byte_array());
                break;
            case rclcpp::PARAMETER_BOOL_ARRAY:
                success = TryUpdate(full_name, param.as_bool_array());
                break;
            case rclcpp::PARAMETER_INTEGER_ARRAY:
                success = TryUpdate(full_name, param.as_integer_array());
                break;
            case rclcpp::PARAMETER_DOUBLE_ARRAY:
                success = TryUpdate(full_name, param.as_double_array());
                break;
            case rclcpp::PARAMETER_STRING_ARRAY:
                success = TryUpdate(full_name, param.as_string_array());
                break;
            default:
                break;
        }
        */
        // Failure could happen in two main cases:
        //  - The parameter does not exist
        //  - The parameter's type as declared does not match the parameter's current type
        if (!success) {
            SPDLOG_WARN("Failed to set parameter {}", param.name);
            all_succeeded = false;
        }
    }

    SetParametersResult set_parameters_result;
    set_parameters_result.successful = all_succeeded;
    return set_parameters_result;
}

std::string ROS2ParamProvider::ConvertFullNameToROS2(const std::string& full_name) {
    std::string ros2_name;

    ros2_name.reserve(full_name.size());
    for (size_t char_idx = 0; char_idx < full_name.size() - 1; char_idx++) {
        if (full_name[char_idx] == ':' && full_name[char_idx + 1] == ':') {
            ros2_name.push_back('.');
            char_idx++;
        } else {
            ros2_name.push_back(full_name[char_idx]);
        }
    }
    ros2_name.push_back(full_name.back());

    return ros2_name;
}

std::string ROS2ParamProvider::ConvertFullNameFromROS2(const std::string& ros2_name) {
    std::string full_name;

    full_name.reserve(ros2_name.size());
    for (char c : ros2_name) {
        if (c == '.') {
            full_name.append("::");
        } else {
            full_name.push_back(c);
        }
    }
    return full_name;
}

#define DECLARE_AND_UPDATE_PARAMS(type)                                                   \
    for (const auto& [param_name, param] : GetParamMap<type>()) {                         \
        rcl_interfaces::msg::ParameterDescriptor descriptor;                              \
        descriptor.description = param->help();                                           \
        const std::string& ros2_param_name = ConvertFullNameToROS2(param_name);           \
        const type& val =                                                                 \
            node->declare_parameter(ros2_param_name, param->default_value(), descriptor); \
        Update(param_name, val);                                                          \
    }

void ROS2ParamProvider::DeclareParameters(rclcpp::Node* node) {
    // Declare the parameters
    DECLARE_AND_UPDATE_PARAMS(bool)
    DECLARE_AND_UPDATE_PARAMS(int64_t)
    DECLARE_AND_UPDATE_PARAMS(double)
    DECLARE_AND_UPDATE_PARAMS(std::string)
    DECLARE_AND_UPDATE_PARAMS(std::vector<uint8_t>)
    DECLARE_AND_UPDATE_PARAMS(std::vector<bool>)
    DECLARE_AND_UPDATE_PARAMS(std::vector<int64_t>)
    DECLARE_AND_UPDATE_PARAMS(std::vector<double>)
    DECLARE_AND_UPDATE_PARAMS(std::vector<std::string>)
}
#undef DECLARE_AND_UPDATE_PARAMS

/*void ROS2ParamProvider::InitUpdateParamCallbacks(rclcpp::Node* node) {
    using rcl_interfaces::msg::SetParametersResult;
    const auto on_update =
        [this](const std::vector<rcl_interfaces::msg::Parameter_<std::allocator<void>>>& params) {
        return UpdateParameters(params);
    };
    callback_handle_ = node->add_on_set_parameters_callback(on_update);
}*/
}  // namespace params
