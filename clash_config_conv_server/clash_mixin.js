module.exports.parse = async ({content, name, url}, {yaml, axios, notify}) => {
    const response = await axios.post('http://host:5555', {
        content: content
    });
    return response.data.content;
}